#!/usr/bin/env python3
"""
Minimal HTTP/1.1 server in pure Python (socket module only).
No http.server, Flask, or Django.
"""

import json
import mimetypes
import os
import re
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote


class HTTPRequest:
    """Parse an HTTP/1.1 request from raw bytes."""

    def __init__(self, data: bytes):
        self.raw = data
        self.method = "GET"
        self.path = "/"
        self.http_version = "HTTP/1.1"
        self.headers = {}
        self.body = b""
        self.query_string = ""
        self._parse(data)

    def _parse(self, data: bytes):
        if not data:
            return
        # Split headers and body
        header_end = data.find(b"\r\n\r\n")
        if header_end == -1:
            header_end = data.find(b"\n\n")
            sep_len = 2
        else:
            sep_len = 4

        if header_end == -1:
            header_data = data
        else:
            header_data = data[:header_end]
            self.body = data[header_end + sep_len:]

        # Decode headers safely
        try:
            header_text = header_data.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            header_text = header_data.decode("iso-8859-1", errors="replace")

        lines = header_text.replace("\r\n", "\n").split("\n")
        if not lines or not lines[0].strip():
            return

        # Request line: METHOD PATH HTTP/1.1
        parts = lines[0].split()
        if len(parts) >= 2:
            self.method = parts[0].upper()
            self.path = parts[1]
            if len(parts) >= 3:
                self.http_version = parts[2]

        # Separate query string
        if "?" in self.path:
            self.path, self.query_string = self.path.split("?", 1)
        self.path = unquote(self.path)

        # Headers
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                self.headers[key.strip().lower()] = value.strip()

    @property
    def content_length(self) -> int:
        try:
            return int(self.headers.get("content-length", 0))
        except (ValueError, TypeError):
            return 0

    def json(self):
        """Parse body as JSON if Content-Type is application/json."""
        ct = self.headers.get("content-type", "")
        if "application/json" in ct or self.body:
            try:
                return json.loads(self.body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None
        return None


class HTTPResponse:
    """Build an HTTP/1.1 response."""

    STATUS_TEXTS = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
    }

    def __init__(self, status: int = 200, body: bytes = b"", headers: dict = None):
        self.status = status
        self.body = body
        self.headers = headers or {}
        if "content-type" not in self.headers:
            if isinstance(body, bytes) and body.startswith(b"{"):
                self.headers["content-type"] = "application/json; charset=utf-8"
            elif isinstance(body, str):
                self.headers["content-type"] = "text/plain; charset=utf-8"
                self.body = body.encode("utf-8")
            else:
                self.headers["content-type"] = "application/octet-stream"

    @classmethod
    def json(cls, data, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        headers = {"content-type": "application/json; charset=utf-8"}
        return cls(status=status, body=body, headers=headers)

    @classmethod
    def text(cls, text: str, status: int = 200):
        body = text.encode("utf-8")
        headers = {"content-type": "text/plain; charset=utf-8"}
        return cls(status=status, body=body, headers=headers)

    def to_bytes(self) -> bytes:
        status_text = self.STATUS_TEXTS.get(self.status, "Unknown")
        lines = [f"HTTP/1.1 {self.status} {status_text}"]
        for key, value in self.headers.items():
            lines.append(f"{key}: {value}")
        lines.append(f"content-length: {len(self.body)}")
        lines.append("connection: close")
        header_bytes = "\r\n".join(lines).encode("utf-8")
        return header_bytes + b"\r\n\r\n" + self.body


class Route:
    """A route with optional path parameters like /users/<id>."""

    def __init__(self, pattern: str, methods: list, handler):
        self.pattern = pattern
        self.methods = [m.upper() for m in methods]
        self.handler = handler
        self.regex, self.param_names = self._compile(pattern)

    def _compile(self, pattern: str):
        # Convert /users/<id> to regex with named groups
        param_names = []
        # Escape regex special chars except < >
        parts = []
        i = 0
        while i < len(pattern):
            if pattern[i] == "<":
                j = pattern.find(">", i)
                if j == -1:
                    parts.append(re.escape(pattern[i]))
                    i += 1
                else:
                    name = pattern[i + 1:j]
                    param_names.append(name)
                    parts.append(r"([^/]+)")
                    i = j + 1
            else:
                parts.append(re.escape(pattern[i]))
                i += 1
        regex_pattern = "^" + "".join(parts) + "$"
        return re.compile(regex_pattern), param_names

    def match(self, method: str, path: str):
        if method.upper() not in self.methods:
            return None
        m = self.regex.match(path)
        if not m:
            return None
        return {name: unquote(value) for name, value in zip(self.param_names, m.groups())}


class HTTPServer:
    """Minimal HTTP/1.1 server with routing and thread pool."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, static_dir: str = None):
        self.host = host
        self.port = port
        self.static_dir = static_dir
        self.routes = []
        self._socket = None
        self._executor = ThreadPoolExecutor(max_workers=50)
        self._running = False
        self._lock = threading.Lock()

    def route(self, path: str, methods=None):
        """Decorator to register a route."""
        if methods is None:
            methods = ["GET"]

        def decorator(func):
            self.add_route(path, methods, func)
            return func

        return decorator

    def add_route(self, path: str, methods: list, handler):
        """Register a route handler."""
        with self._lock:
            self.routes.append(Route(path, methods, handler))

    def _match_route(self, method: str, path: str):
        """Find matching route and return (handler, params)."""
        for route in self.routes:
            params = route.match(method, path)
            if params is not None:
                return route.handler, params
        return None, None

    def _serve_static(self, path: str) -> HTTPResponse:
        """Serve a file from static_dir."""
        if not self.static_dir:
            return None
        # Security: prevent directory traversal
        safe_path = os.path.normpath(path).lstrip("/")
        if safe_path.startswith("..") or "/../" in safe_path:
            return HTTPResponse.text("Forbidden", status=403)
        full_path = os.path.join(self.static_dir, safe_path)
        if not os.path.isfile(full_path):
            return None
        try:
            with open(full_path, "rb") as f:
                data = f.read()
            content_type, _ = mimetypes.guess_type(full_path)
            if content_type is None:
                content_type = "application/octet-stream"
            headers = {"content-type": content_type}
            return HTTPResponse(status=200, body=data, headers=headers)
        except (IOError, OSError):
            return HTTPResponse.text("Internal Server Error", status=500)

    def _handle_request(self, request: HTTPRequest) -> HTTPResponse:
        """Dispatch request to handler."""
        handler, params = self._match_route(request.method, request.path)
        if handler:
            try:
                return handler(request, **params)
            except Exception as e:
                return HTTPResponse.json({"error": str(e)}, status=500)

        # Try static file serving
        if request.method == "GET":
            static_resp = self._serve_static(request.path)
            if static_resp:
                return static_resp

        return HTTPResponse.text("Not Found", status=404)

    def _handle_client(self, client_sock: socket.socket, addr):
        """Handle a single client connection."""
        try:
            client_sock.settimeout(5.0)
            # Read request
            data = b""
            while True:
                try:
                    chunk = client_sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    # Check if we have full headers
                    if b"\r\n\r\n" in data or b"\n\n" in data:
                        # Check content-length for body
                        req = HTTPRequest(data)
                        if len(data) >= data.find(b"\r\n\r\n") + 4 + req.content_length:
                            break
                        if len(data) >= data.find(b"\n\n") + 2 + req.content_length:
                            break
                except socket.timeout:
                    break

            if data:
                request = HTTPRequest(data)
                response = self._handle_request(request)
                client_sock.sendall(response.to_bytes())
        finally:
            try:
                client_sock.close()
            except OSError:
                pass

    def start(self):
        """Start the server (non-blocking)."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.host, self.port))
        self._socket.listen(128)
        self.host, self.port = self._socket.getsockname()
        self._running = True

        def accept_loop():
            while self._running:
                try:
                    self._socket.settimeout(1.0)
                    client_sock, addr = self._socket.accept()
                    self._executor.submit(self._handle_client, client_sock, addr)
                except socket.timeout:
                    continue
                except OSError:
                    break

        self._accept_thread = threading.Thread(target=accept_loop, daemon=True)
        self._accept_thread.start()
        return self

    def stop(self):
        """Stop the server."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
        self._executor.shutdown(wait=False)
        return self

    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


# ---------------------------------------------------------------------------
# TestClient: connect via socket to make requests against the server
# ---------------------------------------------------------------------------

class TestClient:
    def __init__(self, server: HTTPServer):
        self.server = server

    def request(self, method: str, path: str, body: bytes = None, headers: dict = None) -> HTTPResponse:
        headers = headers or {}
        lines = [f"{method.upper()} {path} HTTP/1.1", f"Host: {self.server.host}:{self.server.port}"]
        if body:
            lines.append(f"Content-Length: {len(body)}")
        for k, v in headers.items():
            lines.append(f"{k}: {v}")
        lines.append("")
        request_bytes = "\r\n".join(lines).encode("utf-8")
        if body:
            request_bytes += b"\r\n" + body
        else:
            request_bytes += b"\r\n"

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(5.0)
            sock.connect((self.server.host, self.server.port))
            sock.sendall(request_bytes)

            # Read response
            data = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                except socket.timeout:
                    break
        finally:
            sock.close()

        # Parse response
        header_end = data.find(b"\r\n\r\n")
        if header_end == -1:
            header_end = data.find(b"\n\n")
            sep = 2
        else:
            sep = 4

        body = data[header_end + sep:] if header_end != -1 else b""
        # Parse status line
        status = 200
        resp_headers = {}
        if data:
            header_text = data[:header_end].decode("utf-8", errors="replace")
            lines = header_text.replace("\r\n", "\n").split("\n")
            if lines and lines[0]:
                parts = lines[0].split()
                if len(parts) >= 2:
                    try:
                        status = int(parts[1])
                    except ValueError:
                        pass
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    resp_headers[k.strip().lower()] = v.strip()

        resp = HTTPResponse(status=status, body=body, headers=resp_headers)
        return resp

    def get(self, path: str, headers: dict = None) -> HTTPResponse:
        return self.request("GET", path, headers=headers)

    def post(self, path: str, json_data=None, body: bytes = None, headers: dict = None) -> HTTPResponse:
        hdrs = headers or {}
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            hdrs.setdefault("content-type", "application/json")
        return self.request("POST", path, body=body, headers=hdrs)

    def put(self, path: str, json_data=None, body: bytes = None, headers: dict = None) -> HTTPResponse:
        hdrs = headers or {}
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            hdrs.setdefault("content-type", "application/json")
        return self.request("PUT", path, body=body, headers=hdrs)

    def delete(self, path: str, headers: dict = None) -> HTTPResponse:
        return self.request("DELETE", path, headers=headers)


# ---------------------------------------------------------------------------
# run_tests: all required tests must pass
# ---------------------------------------------------------------------------

def run_tests():
    import tempfile
    import time

    # Create server
    server = HTTPServer(host="127.0.0.1", port=0)

    @server.route("/hello", methods=["GET"])
    def hello(request):
        return HTTPResponse.text("Hello, World!")

    @server.route("/echo", methods=["POST"])
    def echo(request):
        data = request.json()
        return HTTPResponse.json(data if data is not None else {})

    @server.route("/users/<id>", methods=["GET"])
    def get_user(request, id):
        return HTTPResponse.json({"id": id})

    # Static file setup
    with tempfile.TemporaryDirectory() as tmpdir:
        server.static_dir = tmpdir
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("static content")

        server.start()
        time.sleep(0.1)  # Let server start accepting
        client = TestClient(server)

        results = []

        # Test 1: GET /hello returns "Hello, World!"
        try:
            resp = client.get("/hello")
            body_text = resp.body.decode("utf-8")
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            assert body_text == "Hello, World!", f"Expected 'Hello, World!', got {body_text}"
            results.append("PASS: GET /hello")
        except Exception as e:
            results.append(f"FAIL: GET /hello - {e}")

        # Test 2: POST /echo echoes JSON body
        try:
            payload = {"message": "hello", "num": 42}
            resp = client.post("/echo", json_data=payload)
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = json.loads(resp.body.decode("utf-8"))
            assert data == payload, f"Expected {payload}, got {data}"
            results.append("PASS: POST /echo")
        except Exception as e:
            results.append(f"FAIL: POST /echo - {e}")

        # Test 3: GET /users/42 returns {"id": "42"}
        try:
            resp = client.get("/users/42")
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = json.loads(resp.body.decode("utf-8"))
            assert data == {"id": "42"}, f"Expected {{'id': '42'}}, got {data}"
            results.append("PASS: GET /users/42")
        except Exception as e:
            results.append(f"FAIL: GET /users/42 - {e}")

        # Test 4: 404 for undefined routes
        try:
            resp = client.get("/not-a-route")
            assert resp.status == 404, f"Expected 404, got {resp.status}"
            results.append("PASS: 404 undefined route")
        except Exception as e:
            results.append(f"FAIL: 404 undefined route - {e}")

        # Test 5: Concurrent requests: 10 threads all succeed
        try:
            successes = []
            errors = []

            def worker():
                try:
                    r = client.get("/hello")
                    assert r.status == 200
                    successes.append(True)
                except Exception as exc:
                    errors.append(str(exc))

            threads = [threading.Thread(target=worker) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

            assert len(successes) == 10, f"Expected 10 successes, got {len(successes)}; errors: {errors}"
            results.append("PASS: 10 concurrent requests")
        except Exception as e:
            results.append(f"FAIL: concurrent requests - {e}")

        # Extra: static file serving
        try:
            resp = client.get("/test.txt")
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            body_text = resp.body.decode("utf-8")
            assert body_text == "static content", f"Expected 'static content', got {body_text}"
            results.append("PASS: static file serving")
        except Exception as e:
            results.append(f"FAIL: static file serving - {e}")

        server.stop()

        print("\n".join(results))
        passed = sum(1 for r in results if r.startswith("PASS"))
        failed = sum(1 for r in results if r.startswith("FAIL"))
        print(f"\nTotal: {passed} passed, {failed} failed")
        return failed == 0


if __name__ == "__main__":
    ok = run_tests()
    exit(0 if ok else 1)
