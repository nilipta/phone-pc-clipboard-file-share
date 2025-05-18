import http.server
import socketserver
import urllib.parse
import os
import socket
import sys
import threading

PORT = 8000
UPLOAD_DIR = r"R:\uploads"

# Add this line before defining your handler or starting the server:
os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
        
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # List files in UPLOAD_DIR
            try:
                files = os.listdir(UPLOAD_DIR)
            except Exception:
                files = []

            file_list_html = "<ul>"
            for fname in files:
                file_url = f"/uploads/{urllib.parse.quote(fname)}"
                file_list_html += f'<li><a href="{file_url}" target="_blank">{fname}</a></li>'
            file_list_html += "</ul>"

            html = f"""
            <!DOCTYPE html>
            <html lang="en">
              <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>Text & File Upload</title>
              </head>
              <body>
                <h2>Upload Your Text</h2>
                <form action="/" method="post">
                  <textarea name="textbox" rows="4" cols="50"></textarea><br />
                  <input type="submit" value="Upload" />
                </form>

                <h2>Upload a File</h2>
                <form id="uploadForm">
                  <input type="file" name="file" id="fileInput" multiple /><br /><br />
                  <input type="submit" value="Upload" />
                </form>
                <progress id="progressBar" value="0" max="100" style="width:300px; display:none;"></progress>
                <span id="progressText"></span>

                <script>
                document.getElementById('uploadForm').onsubmit = function(e) {{
                  e.preventDefault();
                  var fileInput = document.getElementById('fileInput');
                  var files = fileInput.files;
                  if (!files.length) return;

                  var formData = new FormData();
                  for (let i = 0; i < files.length; i++) {{
                    formData.append('file', files[i]);
                  }}

                  var xhr = new XMLHttpRequest();
                  xhr.open('POST', '/', true);

                  xhr.upload.onprogress = function(e) {{
                    if (e.lengthComputable) {{
                      var percent = Math.round((e.loaded / e.total) * 100);
                      document.getElementById('progressBar').style.display = '';
                      document.getElementById('progressBar').value = percent;
                      document.getElementById('progressText').textContent = percent + '%';
                    }}
                  }};

                  xhr.onload = function() {{
                    if (xhr.status == 200 || xhr.status == 303) {{
                      document.getElementById('progressText').textContent = 'Upload complete!';
                      setTimeout(function() {{ location.reload(); }}, 1000);
                    }} else {{
                      document.getElementById('progressText').textContent = 'Upload failed!';
                    }}
                  }};

                  xhr.send(formData);
                }};
                </script>

                <h2>Files in R:\\uploads</h2>
                {file_list_html}
              </body>
            </html>
            """
            self.wfile.write(html.encode())
        elif self.path.startswith("/uploads/"):
            fname = urllib.parse.unquote(self.path[len("/uploads/"):])
            file_path = os.path.join(UPLOAD_DIR, fname)
            if os.path.isfile(file_path):
                self.send_response(200)
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.send_header("Content-type", "application/octet-stream")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "Not found")


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
