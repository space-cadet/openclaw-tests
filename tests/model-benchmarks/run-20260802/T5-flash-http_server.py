#!/usr/bin/env python3
"""
Minimal HTTP/1.1 server in Python using only the socket module.
No http.server, Flask, or Django.
"""

import socket
import threading
import json
import os
import re
import urllib.parse
import time
from typing import Callable, Dict, Any, Optional, Tuple, List


class HTTPRequest:
    """Represents a parsed HTTP request."""
    
    def __init__(self):
        self.method: str = ""
        self.path: str = ""
        self.version: str = ""
        self.headers: Dict[str, str] = {}
        self.body: bytes = b""
        self.query_params: Dict[str, str] = {}
    
    def json(self) -> Any:
        """Parse body as JSON."""
        if not self.body:
            return None
        return json.loads(self.body.decode('utf-8'))
    
    def text(self) -> str:
        """Return body as text."""
        return self.body.decode('utf-8') if self.body else ""


class HTTPResponse:
    """Represents an HTTP response."""
    
    def __init__(self, status: int = 200, body: Any = None, headers: Optional[Dict[str, str]] = None):
        self.status = status
        self.body = body
        self.headers = headers or {}
    
    def to_bytes(self) -> bytes:
        """Serialize response to HTTP/1.1 bytes."""
        status_text = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }.get(self.status, "Unknown")
        
        # Determine body content and content-type
        body_bytes = b""
        if self.body is not None:
            if isinstance(self.body, (dict, list)):
                body_bytes = json.dumps(self.body).encode('utf-8')
                self.headers.setdefault('Content-Type', 'application/json')
            elif isinstance(self.body, str):
                body_bytes = self.body.encode('utf-8')
                self.headers.setdefault('Content-Type', 'text/plain; charset=utf-8')
            elif isinstance(self.body, bytes):
                body_bytes = self.body
            else:
                body_bytes = str(self.body).encode('utf-8')
        
        self.headers.setdefault('Content-Length', str(len(body_bytes)))
        self.headers.setdefault('Connection', 'close')
        
        # Build response
        lines = [f"HTTP/1.1 {self.status} {status_text}"]
        for key, value in self.headers.items():
            lines.append(f"{key}: {value}")
        lines.append("")
        
        header_bytes = "\r\n".join(lines).encode('utf-8') + b"\r\n"
        return header_bytes + body_bytes


class HTTPServer:
    """Minimal HTTP/1.1 server with routing and thread pool."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.routes: Dict[Tuple[str, str], Callable] = {}
        self.static_dir: Optional[str] = None
        self.thread_pool_size = 10
        self._server_thread: Optional[threading.Thread] = None
    
    def route(self, path_pattern: str, methods: Optional[List[str]] = None):
        """Decorator to register a route handler."""
        if methods is None:
            methods = ["GET"]
        
        def decorator(handler: Callable):
            for method in methods:
                self.routes[(method.upper(), path_pattern)] = handler
            return handler
        return decorator
    
    def set_static_dir(self, directory: str):
        """Set directory for static file serving."""
        self.static_dir = directory
    
    def _parse_request(self, data: bytes) -> Optional[HTTPRequest]:
        """Parse raw HTTP request bytes into HTTPRequest object."""
        try:
            # Split headers and body
            header_end = data.find(b"\r\n\r\n")
            if header_end == -1:
                return None
            
            header_bytes = data[:header_end]
            body = data[header_end + 4:]
            
            # Parse request line and headers
            lines = header_bytes.decode('utf-8', errors='replace').split('\r\n')
            if not lines:
                return None
            
            # Request line: METHOD PATH HTTP/VERSION
            request_line = lines[0]
            parts = request_line.split(' ')
            if len(parts) < 3:
                return None
            
            req = HTTPRequest()
            req.method = parts[0].upper()
            req.path = parts[1]
            req.version = parts[2]
            req.body = body
            
            # Parse query params
            if '?' in req.path:
                path_part, query_part = req.path.split('?', 1)
                req.path = path_part
                req.query_params = urllib.parse.parse_qs(query_part, keep_blank_values=True)
                req.query_params = {k: v[0] if len(v) == 1 else v for k, v in req.query_params.items()}
            
            # Parse headers
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    req.headers[key.strip()] = value.strip()
            
            # Handle Content-Length for body truncation/padding
            if 'Content-Length' in req.headers:
                content_length = int(req.headers['Content-Length'])
                req.body = req.body[:content_length]
            
            return req
        except Exception:
            return None
    
    def _match_route(self, method: str, path: str) -> Tuple[Optional[Callable], Dict[str, str]]:
        """Match a route and extract path parameters."""
        # Try exact match first
        handler = self.routes.get((method, path))
        if handler:
            return handler, {}
        
        # Try pattern matching with path params
        for (route_method, route_pattern), handler in self.routes.items():
            if route_method != method:
                continue
            
            regex_pattern = "^" + re.sub(r'<([^>]+)>', r'(?P<\1>[^/]+)', route_pattern) + "$"
            match = re.match(regex_pattern, path)
            if match:
                return handler, match.groupdict()
        
        return None, {}
    
    def _serve_static(self, path: str) -> Optional[HTTPResponse]:
        """Try to serve a static file."""
        if not self.static_dir:
            return None
        
        safe_path = path.lstrip('/')
        if '..' in safe_path or safe_path.startswith('/'):
            return None
        
        file_path = os.path.join(self.static_dir, safe_path)
        
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                content_type = "application/octet-stream"
                if file_path.endswith('.html'):
                    content_type = "text/html; charset=utf-8"
                elif file_path.endswith('.css'):
                    content_type = "text/css; charset=utf-8"
                elif file_path.endswith('.js'):
                    content_type = "application/javascript; charset=utf-8"
                elif file_path.endswith('.json'):
                    content_type = "application/json"
                elif file_path.endswith('.txt'):
                    content_type = "text/plain; charset=utf-8"
                elif file_path.endswith('.png'):
                    content_type = "image/png"
                elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                    content_type = "image/jpeg"
                
                return HTTPResponse(200, content, {"Content-Type": content_type})
            except Exception:
                return None
        
        return None
    
    def _handle_request(self, req: HTTPRequest) -> HTTPResponse:
        """Handle a parsed request and return a response."""
        handler, path_params = self._match_route(req.method, req.path)
        
        if handler:
            try:
                return handler(req, **path_params)
            except Exception as e:
                return HTTPResponse(500, {"error": str(e)})
        
        if req.method == "GET":
            static_response = self._serve_static(req.path)
            if static_response:
                return static_response
        
        return HTTPResponse(404, {"error": "Not found"})
    
    def _client_handler(self, client_socket: socket.socket, addr: Tuple[str, int]):
        """Handle a single client connection."""
        try:
            client_socket.settimeout(30)
            
            # Read request
            data = b""
            while True:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    
                    # Check if we have complete headers
                    if b"\r\n\r\n" in data:
                        header_end = data.find(b"\r\n\r\n")
                        headers_data = data[:header_end].decode('utf-8', errors='replace')
                        
                        content_length = 0
                        for line in headers_data.split('\r\n'):
                            if line.lower().startswith('content-length:'):
                                content_length = int(line.split(':', 1)[1].strip())
                                break
                        
                        total_needed = header_end + 4 + content_length
                        if len(data) >= total_needed:
                            break
                except socket.timeout:
                    break
            
            if data:
                req = self._parse_request(data)
                if req:
                    response = self._handle_request(req)
                else:
                    response = HTTPResponse(400, {"error": "Bad request"})
                
                resp_bytes = response.to_bytes()
                try:
                    client_socket.sendall(resp_bytes)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
        except Exception as e:
            print(f"[SERVER ERROR] {e}", flush=True)
        finally:
            try:
                client_socket.close()
            except Exception:
                pass
    
    def start(self, blocking: bool = False):
        """Start the server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(self.thread_pool_size)
        
        self.host, self.port = self.socket.getsockname()
        self.running = True
        
        if blocking:
            self._accept_loop()
        else:
            self._server_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._server_thread.start()
    
    def _accept_loop(self):
        """Main accept loop."""
        while self.running:
            try:
                self.socket.settimeout(1.0)
                try:
                    client_socket, addr = self.socket.accept()
                except socket.timeout:
                    continue
                
                thread = threading.Thread(target=self._client_handler, args=(client_socket, addr), daemon=True)
                thread.start()
            except OSError:
                break
            except Exception:
                continue
    
    def stop(self):
        """Stop the server."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None


class TestClient:
    """Test client for making requests to the server."""
    
    def __init__(self, server: HTTPServer):
        self.server = server
    
    def request(self, method: str, path: str, body: Any = None, headers: Optional[Dict[str, str]] = None) -> HTTPResponse:
        """Make a request and return the parsed response."""
        headers = headers or {}
        
        # Build request
        request_lines = [f"{method.upper()} {path} HTTP/1.1"]
        request_lines.append(f"Host: {self.server.host}:{self.server.port}")
        
        body_bytes = b""
        if body is not None:
            if isinstance(body, (dict, list)):
                body_bytes = json.dumps(body).encode('utf-8')
                headers.setdefault('Content-Type', 'application/json')
            elif isinstance(body, str):
                body_bytes = body.encode('utf-8')
            elif isinstance(body, bytes):
                body_bytes = body
            else:
                body_bytes = str(body).encode('utf-8')
            headers.setdefault('Content-Length', str(len(body_bytes)))
        
        for key, value in headers.items():
            request_lines.append(f"{key}: {value}")
        
        request_lines.append("")
        request_data = "\r\n".join(request_lines).encode('utf-8') + b"\r\n" + body_bytes
        
        # Send request
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        try:
            sock.connect((self.server.host, self.server.port))
            sock.sendall(request_data)
            
            # Read response - for HTTP/1.1 with Connection: close, read until connection closes
            response_data = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
            except socket.timeout:
                pass
        except Exception as e:
            return HTTPResponse(0, f"Client error: {e}")
        finally:
            sock.close()
        
        return self._parse_response(response_data)
    
    def _parse_response(self, data: bytes) -> HTTPResponse:
        """Parse raw HTTP response bytes."""
        if not data:
            return HTTPResponse(0, "No response")
        
        header_end = data.find(b"\r\n\r\n")
        if header_end == -1:
            return HTTPResponse(0, "Invalid response")
        
        header_bytes = data[:header_end]
        body = data[header_end + 4:]
        
        lines = header_bytes.decode('utf-8', errors='replace').split('\r\n')
        if not lines:
            return HTTPResponse(0, "Invalid response")
        
        # Parse status line
        status_parts = lines[0].split(' ')
        status = int(status_parts[1]) if len(status_parts) > 1 and status_parts[1].isdigit() else 0
        
        # Parse headers
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        
        # Parse body based on content-type
        body_content = body
        if body:
            content_type = headers.get('Content-Type', '')
            if 'application/json' in content_type:
                try:
                    body_content = json.loads(body.decode('utf-8'))
                except Exception:
                    body_content = body.decode('utf-8')
            else:
                body_content = body.decode('utf-8')
        
        return HTTPResponse(status, body_content, headers)
    
    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> HTTPResponse:
        return self.request("GET", path, headers=headers)
    
    def post(self, path: str, body: Any = None, headers: Optional[Dict[str, str]] = None) -> HTTPResponse:
        return self.request("POST", path, body=body, headers=headers)
    
    def put(self, path: str, body: Any = None, headers: Optional[Dict[str, str]] = None) -> HTTPResponse:
        return self.request("PUT", path, body=body, headers=headers)
    
    def delete(self, path: str, headers: Optional[Dict[str, str]] = None) -> HTTPResponse:
        return self.request("DELETE", path, headers=headers)


def run_tests():
    """Run all tests. Must pass all 5 test cases."""
    # Create server
    server = HTTPServer("127.0.0.1", 0)
    
    # Register routes
    @server.route("/hello")
    def hello_handler(req: HTTPRequest) -> HTTPResponse:
        return HTTPResponse(200, "Hello, World!")
    
    @server.route("/echo", methods=["POST"])
    def echo_handler(req: HTTPRequest) -> HTTPResponse:
        return HTTPResponse(200, req.json())
    
    @server.route("/users/<id>")
    def users_handler(req: HTTPRequest, id: str) -> HTTPResponse:
        return HTTPResponse(200, {"id": id})
    
    # Start server
    server.start()
    time.sleep(0.2)
    
    # Create test client
    client = TestClient(server)
    
    print("=" * 50)
    print("Running HTTP Server Tests")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    # Test 1: GET /hello returns "Hello, World!"
    print("\nTest 1: GET /hello")
    try:
        response = client.get("/hello")
        assert response.status == 200, f"Expected 200, got {response.status}"
        assert response.body == "Hello, World!", f"Expected 'Hello, World!', got {response.body}"
        print("  PASSED: GET /hello returns 'Hello, World!'")
        passed += 1
    except AssertionError as e:
        print(f"  FAILED: {e}")
        failed += 1
    
    # Test 2: POST /echo echoes JSON body
    print("\nTest 2: POST /echo")
    try:
        test_body = {"message": "hello", "number": 42}
        response = client.post("/echo", body=test_body)
        assert response.status == 200, f"Expected 200, got {response.status}"
        assert response.body == test_body, f"Expected {test_body}, got {response.body}"
        print("  PASSED: POST /echo echoes JSON body")
        passed += 1
    except AssertionError as e:
        print(f"  FAILED: {e}")
        failed += 1
    
    # Test 3: GET /users/42 returns {"id": "42"}
    print("\nTest 3: GET /users/42")
    try:
        response = client.get("/users/42")
        assert response.status == 200, f"Expected 200, got {response.status}"
        assert response.body == {"id": "42"}, f"Expected {{'id': '42'}}, got {response.body}"
        print("  PASSED: GET /users/42 returns correct JSON")
        passed += 1
    except AssertionError as e:
        print(f"  FAILED: {e}")
        failed += 1
    
    # Test 4: 404 for undefined routes
    print("\nTest 4: 404 for undefined routes")
    try:
        response = client.get("/undefined-route")
        assert response.status == 404, f"Expected 404, got {response.status}"
        print("  PASSED: Undefined routes return 404")
        passed += 1
    except AssertionError as e:
        print(f"  FAILED: {e}")
        failed += 1
    
    # Test 5: Concurrent requests - 10 threads all succeed
    print("\nTest 5: Concurrent requests (10 threads)")
    try:
        results = []
        errors = []
        
        def make_request(thread_id: int):
            try:
                resp = client.get("/hello")
                results.append((thread_id, resp.status, resp.body))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=30)
        
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}: {errors}"
        
        for thread_id, status, body in results:
            assert status == 200, f"Thread {thread_id}: Expected 200, got {status}"
            assert body == "Hello, World!", f"Thread {thread_id}: Expected 'Hello, World!', got {body}"
        
        print(f"  PASSED: All 10 concurrent requests succeeded")
        passed += 1
    except AssertionError as e:
        print(f"  FAILED: {e}")
        failed += 1
    
    # Stop server
    server.stop()
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
