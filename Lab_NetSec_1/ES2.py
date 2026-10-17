import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
 
HOST = "0.0.0.0"
PORT = 8080
 
notes = {}                 
next_id = 1
notes_lock = threading.Lock()
 
 
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"      
 
   
    def log_message(self, *args):      
        pass
 
    def send_json(self, status, obj, extra_headers=None):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)
 
    def send_empty(self, status):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()
 
    def error(self, status, msg, extra_headers=None):
        self.send_json(status, {"error": msg}, extra_headers)
 
    def method_not_allowed(self, allowed):
        self.error(405, "method not allowed", {"Allow": ", ".join(allowed)})
 
    def read_body(self):
       
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return b""
        if length <= 0:
            return b""
        return self.rfile.read(length)
 
    
    def dispatch(self):
        method = self.command
        body = self.read_body()
        parsed = urlparse(self.path)
        path = parsed.path
 
        if path == "/":
            if method == "GET":
                return self.send_json(200, {"status": "ok"})
            return self.method_not_allowed(["GET"])
 
        if path == "/echo":
            if method != "GET":
                return self.method_not_allowed(["GET"])
            qs = parse_qs(parsed.query, keep_blank_values=True)
            if "msg" not in qs:
                return self.error(400, "missing msg parameter")
            return self.send_json(200, {"msg": qs["msg"][0]})
 
        if path == "/notes":
            if method != "POST":
                return self.method_not_allowed(["POST"])
            return self.create_note(body)
 
        if path.startswith("/notes/"):
            if method not in ("GET", "DELETE"):
                return self.method_not_allowed(["GET", "DELETE"])
            raw_id = path[len("/notes/"):]
            if not (raw_id.isascii() and raw_id.isdigit()):
                return self.error(404, "not found")
            return self.note_by_id(method, int(raw_id))
 
        return self.error(404, "not found")
 
    
    def create_note(self, body):
        global next_id
        ctype = self.headers.get("Content-Type", "")
        if ctype.split(";")[0].strip().lower() != "application/json":
            return self.error(415, "Content-Type must be application/json")
        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self.error(400, "malformed JSON")
        if not isinstance(data, dict) or not isinstance(data.get("text"), str):
            return self.error(400, "'text' must be a string")
        with notes_lock:
            note_id = next_id
            next_id += 1
            notes[note_id] = data["text"]
        return self.send_json(201, {"id": note_id})
 
    def note_by_id(self, method, note_id):
        with notes_lock:
            if note_id not in notes:
                return self.error(404, "not found")
            if method == "GET":
                return self.send_json(200, {"id": note_id, "text": notes[note_id]})
            del notes[note_id]
        return self.send_empty(204)
 
    
    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = dispatch
 
 
class Server(ThreadingHTTPServer):
    request_queue_size = 128           
    daemon_threads = True
 
 
def main():
    server = Server((HOST, PORT), Handler)
    print(f"Listening on {HOST}:{PORT}")
    server.serve_forever()
 
 
if __name__ == "__main__":
    main()
 