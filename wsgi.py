import os
import threading
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer

# 1. Ép robot main.py chạy ngầm trong một luồng (thread) riêng biệt
def run_bot():
    # Thêm PYTHONUNBUFFERED=1 để bắt Python in log ra Render ngay lập tức
    os.environ["PYTHONUNBUFFERED"] = "1"
    subprocess.run(["python", "main.py"])

threading.Thread(target=run_bot, daemon=True).start()

# 2. Tạo một Web Server "giả" ở cổng mà Render yêu cầu để giữ cho ứng dụng luôn Live
class HealthCheckHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Robot is running smoothly!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[SYSTEM] Web Server ao dang mo tai port {port} de duy tri goi Free...")
    server.serve_forever()
