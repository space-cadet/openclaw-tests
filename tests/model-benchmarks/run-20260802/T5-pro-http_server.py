#!/usr/bin/env python3
"""Minimal HTTP/1.1 server using only the socket module."""

import json
import os
import re
import socket
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor


class HTTPRequest:
    """Represents a parsed HTTP request."""

    def __init__(self, raw_request: bytes):
        self.raw = raw_request
        self.method = ""
        self.path = ""
        self.version = ""
        self.headers = {}
        self.body = b""
        self.query_params = {}
        self.path_params = {}
        self._parse()

    def _parse(self):
        try:
            # Split headers and body
            header_end = self.raw.find(b"\r\n\r\n")
            if header_end == -1:
                header_end = self.raw.find(b"\n\n")
                if header_end == -1:
                    return
                header_data = self.raw[:header_end + 2]
                self.body = self.raw[header_end + 2:]
            else:
                header_data = self.raw[:header_end + 2]
                self.body = self.raw[header_end + 4:]

            # Parse request line and headers
            lines = header_data.decode("utf-8", errors="replace").split("\r\n")
            if len(lines) == 1:
                lines = header_data.decode("utf-8", errors="replace").split("\n")

            # Request line: METHOD PATH HTTP/VERSION
            if lines:
                request_line = lines[0].strip()
                parts = request_line.split()
                if len(parts) >= 3:
                    self.method = parts[0]
                    self.path = parts[1]
                    self.version = parts[2]

            # Parse headers
            for line in lines[1:]:
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    self.headers[key.strip().lower()] = value.strip()

            # Parse query parameters
            if "?" in self.path:
                self.path, query = self.path.split("?", 1)
                self.query_params = urllib.parse.parse_qs(query)

            # Parse body based on Content-Type
            content_length = int(self.headers.get("content-length", 0))
            if content_length > 0:
                self.body = self.body[:content_length]

        except Exception:
            pass

    def json(self):
        """Parse body as JSON."""
        try:
            return json.loads(self.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None


class HTTPResponse:
    """Represents an HTTP response."""

    def __init__(self, status_code: int = 200, body: bytes = b"",
                 headers: dict = None, content_type: str = "application/json"):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        self.content_type = content_type

    @classmethod
    def json(cls, data, status_code: int = 200):
        """Create a JSON response."""
        body = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        return cls(status_code, body, headers)

    @classmethod
    def text(cls, text: str, status_code: int = 200):
        """Create a text response."""
        body = text.encode("utf-8")
        headers = {"Content-Type": "text/plain"}
        return cls(status_code, body, headers)

    @classmethod
    def not_found(cls):
        """Create a 404 response."""
        return cls.json({"error": "Not Found"}, 404)

    def to_bytes(self) -> bytes:
        """Convert response to HTTP bytes."""
        status_text = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }.get(self.status_code, "Unknown")

        response = f"HTTP/1.1 {self.status_code} {status_text}\r\n"
        response += f"Content-Type: {self.content_type}\r\n"
        response += f"Content-Length: {len(self.body)}\r\n"
        response += "Connection: close\r\n"

        for key, value in self.headers.items():
            if key.lower() not in ("content-type", "content-length", "connection"):
                response += f"{key}: {value}\r\n"

        response += "\r\n"
        return response.encode("utf-8") + self.body


class HTTPServer:
    """Minimal HTTP/1.1 server with routing and thread pool."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080,
                 max_workers: int = 10, static_dir: str = None):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.static_dir = static_dir
        self.routes = {}  # {("METHOD", "/path/pattern"): handler}
        self.param_routes = []  # [(compiled_regex, param_names, handler)]
        self.server_socket = None
        self.running = False
        self.executor = None

    def route(self, path: str, methods=None):
        """Decorator to register a route handler."""
        if methods is None:
            methods = ["GET"]

        def decorator(func):
            for method in methods:
                # Check for path parameters (e.g., /users/{id})
                param_pattern = r"\{(\w+)\}"
                param_names = re.findall(param_pattern, path)

                if param_names:
                    # Convert to regex pattern
                    regex_path = path
                    for name in param_names:
                        regex_path = regex_path.replace(f"{{{name}}}", r"([^/]+)")
                    pattern = re.compile(f"^{regex_path}$")
                    self.param_routes.append((pattern, param_names, method.upper(), func))
                else:
                    self.routes[(method.upper(), path)] = func
            return func
        return decorator

    def serve_static(self, request: HTTPRequest) -> HTTPResponse:
        """Serve static files from static_dir."""
        if not self.static_dir:
            return HTTPResponse.not_found()

        # Sanitize path to prevent directory traversal
        safe_path = request.path.lstrip("/")
        safe_path = safe_path.replace("..", "")
        file_path = os.path.join(self.static_dir, safe_path)

        # Ensure the path is within static_dir
        real_static = os.path.realpath(self.static_dir)
        real_file = os.path.realpath(file_path)
        if not real_file.startswith(real_static):
            return HTTPResponse.not_found()

        if not os.path.isfile(file_path):
            return HTTPResponse.not_found()

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # Determine content type
            ext = os.path.splitext(file_path)[1].lower()
            content_types = {
                ".html": "text/html",
                ".css": "text/css",
                ".js": "application/javascript",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".txt": "text/plain",
            }
            content_type = content_types.get(ext, "application/octet-stream")

            headers = {"Content-Type": content_type}
            return HTTPResponse(200, content, headers, content_type)
        except Exception:
            return HTTPResponse.json({"error": "Internal Server Error"}, 500)

    def _find_handler(self, request: HTTPRequest):
        """Find the handler for a request."""
        # Check exact routes first
        key = (request.method, request.path)
        if key in self.routes:
            return self.routes[key], {}

        # Check parameterized routes
        for pattern, param_names, method, handler in self.param_routes:
            if method == request.method:
                match = pattern.match(request.path)
                if match:
                    params = dict(zip(param_names, match.groups()))
                    return handler, params

        # Check static files (GET only)
        if request.method == "GET" and self.static_dir:
            return self.serve_static, None

        return None, None

    def _handle_request(self, client_socket: socket.socket, addr):
        """Handle a single client request."""
        try:
            # Read the request
            request_data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                request_data += chunk
                # Check if we have the full headers
                if b"\r\n\r\n" in request_data or b"\n\n" in request_data:
                    # Check content-length for body
                    header_end = request_data.find(b"\r\n\r\n")
                    if header_end == -1:
                        header_end = request_data.find(b"\n\n")
                    headers = request_data[:header_end].decode("utf-8", errors="replace")
                    content_length = 0
                    for line in headers.split("\r\n"):
                        if line.lower().startswith("content-length:"):
                            content_length = int(line.split(":", 1)[1].strip())
                            break
                    if len(request_data) >= header_end + 4 + content_length:
                        break
                    elif len(request_data) >= header_end + 2 + content_length:
                        break

            if not request_data:
                return

            request = HTTPRequest(request_data)

            if not request.method:
                response = HTTPResponse.json({"error": "Bad Request"}, 400)
            else:
                handler, params = self._find_handler(request)
                if handler:
                    if params is not None:
                        request.path_params = params
                    try:
                        response = handler(request)
                        if not isinstance(response, HTTPResponse):
                            response = HTTPResponse.json(response)
                    except Exception as e:
                        response = HTTPResponse.json({"error": str(e)}, 500)
                else:
                    response = HTTPResponse.not_found()

            client_socket.sendall(response.to_bytes())

        except Exception:
            pass
        finally:
            try:
                client_socket.close()
            except Exception:
                pass

    def start(self):
        """Start the server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        print(f"Server started on http://{self.host}:{self.port}")

        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, addr = self.server_socket.accept()
                self.executor.submit(self._handle_request, client_socket, addr)
            except socket.timeout:
                continue
            except OSError:
                break

    def stop(self):
        """Stop the server."""
        self.running = False
        if self.executor:
            self.executor.shutdown(wait=False)
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

    def run_in_thread(self):
        """Run the server in a background thread."""
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        # Give the server a moment to start
        time.sleep(0.1)
        return thread


class TestClient:
    """Simple HTTP client for testing."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port

    def request(self, method: str, path: str, body: dict = None,
                headers: dict = None) -> dict:
        """Send an HTTP request and return parsed response."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((self.host, self.port))

        # Build request
        request_lines = [f"{method} {path} HTTP/1.1"]
        request_lines.append(f"Host: {self.host}:{self.port}")
        request_lines.append("Connection: close")

        if headers:
            for key, value in headers.items():
                request_lines.append(f"{key}: {value}")

        if body is not None:
            body_json = json.dumps(body)
            request_lines.append("Content-Type: application/json")
            request_lines.append(f"Content-Length: {len(body_json.encode())}")
            request_lines.append("")
            request_lines.append(body_json)
        else:
            request_lines.append("")
            request_lines.append("")

        request_text = "\r\n".join(request_lines)
        sock.sendall(request_text.encode())

        # Read response
        response_data = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
            except socket.timeout:
                break

        sock.close()
        return self._parse_response(response_data)

    def _parse_response(self, data: bytes) -> dict:
        """Parse HTTP response bytes."""
        header_end = data.find(b"\r\n\r\n")
        if header_end == -1:
            header_end = data.find(b"\n\n")
            if header_end == -1:
                return {"status": 0, "body": None, "headers": {}}
            headers_bytes = data[:header_end + 2]
            body = data[header_end + 2:]
        else:
            headers_bytes = data[:header_end + 2]
            body = data[header_end + 4:]

        headers_text = headers_bytes.decode("utf-8", errors="replace")
        lines = headers_text.split("\r\n")
        if len(lines) == 1:
            lines = headers_text.split("\n")

        status = 0
        headers = {}
        if lines:
            status_line = lines[0]
            parts = status_line.split()
            if len(parts) >= 2:
                try:
                    status = int(parts[1])
                except ValueError:
                    pass

        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        # Parse body as JSON if content-type is application/json
        content_type = headers.get("content-type", "")
        if "application/json" in content_type and body:
            try:
                body = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = body.decode("utf-8", errors="replace")
        elif body:
            body = body.decode("utf-8", errors="replace")

        return {"status": status, "body": body, "headers": headers}

    def get(self, path: str, headers: dict = None) -> dict:
        return self.request("GET", path, headers=headers)

    def post(self, path: str, body: dict = None, headers: dict = None) -> dict:
        return self.request("POST", path, body, headers)

    def put(self, path: str, body: dict = None, headers: dict = None) -> dict:
        return self.request("PUT", path, body, headers)

    def delete(self, path: str, headers: dict = None) -> dict:
        return self.request("DELETE", path, headers=headers)


def run_tests():
    """Run all tests."""
    print("=" * 50)
    print("Running HTTP Server Tests")
    print("=" * 50)

    # Create server
    server = HTTPServer(host="127.0.0.1", port=0)  # port 0 = auto-assign
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", 0))
    _, port = server_socket.getsockname()
    server_socket.close()
    server.port = port

    # Register routes
    @server.route("/hello", methods=["GET"])
    def hello(request):
        return HTTPResponse.text("Hello, World!")

    @server.route("/echo", methods=["POST"])
    def echo(request):
        return HTTPResponse.json(request.json() or {})

    @server.route("/users/{id}", methods=["GET"])
    def get_user(request):
        return HTTPResponse.json({"id": request.path_params.get("id")})

    @server.route("/users/{id}", methods=["PUT", "DELETE"])
    def update_user(request):
        return HTTPResponse.json({
            "id": request.path_params.get("id"),
            "method": request.method
        })

    # Start server
    server.run_in_thread()
    client = TestClient("127.0.0.1", port)

    tests_passed = 0
    tests_failed = 0

    # Test 1: GET /hello returns "Hello, World!"
    print("\nTest 1: GET /hello")
    try:
        response = client.get("/hello")
        assert response["status"] == 200, f"Expected 200, got {response['status']}"
        assert response["body"] == "Hello, World!", f"Expected 'Hello, World!', got {response['body']}"
        print("  ✓ PASSED")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1

    # Test 2: POST /echo echoes JSON body
    print("\nTest 2: POST /echo")
    try:
        test_body = {"message": "hello", "number": 42}
        response = client.post("/echo", body=test_body)
        assert response["status"] == 200, f"Expected 200, got {response['status']}"
        assert response["body"] == test_body, f"Expected {test_body}, got {response['body']}"
        print("  ✓ PASSED")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1

    # Test 3: GET /users/42 returns {"id": "42"}
    print("\nTest 3: GET /users/42")
    try:
        response = client.get("/users/42")
        assert response["status"] == 200, f"Expected 200, got {response['status']}"
        assert response["body"] == {"id": "42"}, f"Expected {{'id': '42'}}, got {response['body']}"
        print("  ✓ PASSED")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1

    # Test 4: 404 for undefined routes
    print("\nTest 4: 404 for undefined routes")
    try:
        response = client.get("/nonexistent")
        assert response["status"] == 404, f"Expected 404, got {response['status']}"
        print("  ✓ PASSED")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1

    # Test 5: Concurrent requests - 10 threads all succeed
    print("\nTest 5: Concurrent requests (10 threads)")
    try:
        results = []
        errors = []

        def make_request(i):
            try:
                if i % 3 == 0:
                    resp = client.get("/hello")
                elif i % 3 == 1:
                    resp = client.post("/echo", body={"thread": i})
                else:
                    resp = client.get(f"/users/{i}")
                results.append((i, resp))
            except Exception as e:
                errors.append((i, str(e)))

        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        assert len(errors) == 0, f"Errors occurred: {errors}"

        for i, resp in results:
            assert resp["status"] == 200, f"Thread {i} failed with status {resp['status']}"

        print("  ✓ PASSED")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1

    # Additional tests for PUT and DELETE
    print("\nTest 6: PUT /users/123")
    try:
        response = client.put("/users/123", body={"name": "test"})
        assert response["status"] == 200, f"Expected 200, got {response['status']}"
        assert response["body"] == {"id": "123", "method": "PUT"}
        print("  ✓ PASSED")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1

    print("\nTest 7: DELETE /users/123")
    try:
        response = client.delete("/users/123")
        assert response["status"] == 200, f"Expected 200, got {response['status']}"
        assert response["body"] == {"id": "123", "method": "DELETE"}
        print("  ✓ PASSED")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1

    # Clean up
    server.stop()

    print("\n" + "=" * 50)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 50)

    return tests_failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
