import socket
import threading
 
HOST = "0.0.0.0"
PORT = 9001
 
store = {}                 
store_lock = threading.Lock()
 
 
def handle_command(line: str) -> str:
    if line == "PING":
        return "PONG"
 
    if line.startswith("ECHO "):
        text = line[5:]
        return text if text else "ERR"
 
    if line.startswith("SET "):
        parts = line.split(" ", 2)       
        if len(parts) == 3 and parts[1] and parts[2]:
            with store_lock:
                store[parts[1]] = parts[2]
            return "OK"
        return "ERR"
 
    if line.startswith("GET "):
        key = line[4:]
        if not key or " " in key:
            return "ERR"
        with store_lock:
            return store.get(key, "NOT_FOUND")
 
    return "ERR"                          .
 
 
def serve_client(conn: socket.socket) -> None:
    buffer = b""
    with conn:
        while True:
            try:
                data = conn.recv(4096)
            except OSError:
                break
            if not data:                   
                break
            buffer += data
            responses = []
            while b"\n" in buffer:        
                raw, buffer = buffer.split(b"\n", 1)
                line = raw.decode("latin-1")
                responses.append(handle_command(line) + "\n")
            if responses:
                try:
                    conn.sendall("".join(responses).encode("latin-1"))
                except OSError:
                    break
 
 
def main() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(128)
    print(f"Listening on {HOST}:{PORT}")
    while True:
        conn, _ = srv.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        threading.Thread(target=serve_client, args=(conn,), daemon=True).start()
 
 
if __name__ == "__main__":
    main()
 
