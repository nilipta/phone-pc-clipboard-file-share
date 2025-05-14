import http.server
import socketserver
import urllib.parse
import os
import socket
import sys
import threading

PORT = 8000
UPLOAD_DIR = "uploads"


class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):

        content_length = int(self.headers['Content-Length'])
        content_type = self.headers.get('Content-Type')
        
        if content_type and 'multipart/form-data' in content_type:
            # Extract boundary
            boundary = content_type.split("boundary=")[-1].encode()

            # Read request body
            post_data = self.rfile.read(content_length)

            # Split parts
            parts = post_data.split(b"--" + boundary)
            uploaded_files = []
            for part in parts:
                if b"Content-Disposition:" in part:
                    header, file_data = part.split(b"\r\n\r\n", 1)
                    header_str = header.decode(errors="ignore")
                    # Improved filename extraction
                    for line in header_str.split("\r\n"):
                        if "filename=" in line:
                            filename = line.split("filename=")[-1].strip().strip('"')
                            break
                    else:
                        continue  # Skip if no filename (not a file part)

                    if not filename:
                        continue  # Skip empty file fields

                    file_path = os.path.join(UPLOAD_DIR, filename)
                    os.makedirs(UPLOAD_DIR, exist_ok=True)
                    with open(file_path, "wb") as f:
                        # Remove trailing boundary and CRLF
                        f.write(file_data.rstrip(b"\r\n--"))
                    uploaded_files.append(filename)

            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            # Optionally, you can show a message with all uploaded files
            # self.wfile.write(f"<h2>Files uploaded: {', '.join(uploaded_files)}</h2>".encode())
            return

        elif content_length > 0:
            post_data = self.rfile.read(content_length)
            parsed_data = urllib.parse.parse_qs(post_data.decode())

            uploaded_text = parsed_data.get('textbox', [''])[0]

            # Save the uploaded text (optional)
            with open("uploaded_text.txt", "a") as f:
                f.write(uploaded_text + "\n")

            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            return


Handler = MyHandler
# Create a server instance
httpd = socketserver.TCPServer(("", PORT), MyHandler)

def get_local_ips():
    ips = set()
    hostname = socket.gethostname()
    try:
        print(socket.getaddrinfo(hostname, None))
        # Get all addresses associated with the hostname
        for addr in socket.getaddrinfo(hostname, None):
            ip = addr[4][0]
            # Filter out localhost and duplicates
            if not ip.startswith("127.") and ':' not in ip:
                ips.add(ip)
    except Exception:
        pass
    return ips

def signal_handler(sig, frame):
    print("\nGracefully shutting down...")
    threading.Thread(target=httpd.shutdown).start()
    sys.exit(0)

print(f"Serving at http://127.0.0.1:{PORT} (Press Ctrl+C to stop)")
for ip in get_local_ips():
    print(f"Accessible on: http://{ip}:{PORT}")
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    pass

httpd.server_close()  # Ensure cleanup
print("Server stopped.")
