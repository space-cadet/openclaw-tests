# Task T5: Mini HTTP Server

## Difficulty: Hard

Build a minimal HTTP/1.1 server in Python using only standard library.

### Requirements
1. Parse HTTP/1.1 requests (method, path, headers, body)
2. Support GET, POST, PUT, DELETE methods
3. Routing: map URL paths to handler functions
4. Response generation: status codes, headers, JSON body
5. Concurrent request handling (thread pool or async)
6. Static file serving from a directory
7. Basic middleware support (logging, error handling)
8. No `http.server` or Flask/Django — use `socket` module

### Test Cases (must all pass)

```python
# Start server
server = HTTPServer(host="127.0.0.1", port=0)  # port 0 = auto

# Register routes
@server.route("GET", "/hello")
def hello_handler(req):
    return Response(200, {"Content-Type": "text/plain"}, "Hello, World!")

@server.route("POST", "/echo")
def echo_handler(req):
    return Response(200, {"Content-Type": "application/json"}, json.dumps(req.body))

@server.route("GET", "/users/<id>")
def user_handler(req, id):
    return Response(200, {"Content-Type": "application/json"}, json.dumps({"id": id}))

# Test GET
client = TestClient(server)
response = client.get("/hello")
response.status => 200
response.body => "Hello, World!"

# Test POST with body
response = client.post("/echo", body={"msg": "hi"})
response.status => 200
response.json() => {"msg": "hi"}

# Test path parameter
response = client.get("/users/42")
response.status => 200
response.json() => {"id": "42"}

# Test 404
response = client.get("/notfound")
response.status => 404

# Test static file serving
server.serve_static("/static", "./public")
# GET /static/test.txt serves ./public/test.txt

# Test concurrent requests
import threading
results = []
def make_request():
    r = client.get("/hello")
    results.append(r.status)

threads = [threading.Thread(target=make_request) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
all(r == 200 for r in results) => True
```

### Output Format
Write `http_server.py` with `HTTPServer`, `Response`, `TestClient`, and `run_tests()`.

### Scoring
- Correctness: all tests pass
- Concurrency: no request corruption under load
- HTTP compliance: proper request/response parsing
- Code quality: clean routing and middleware design
