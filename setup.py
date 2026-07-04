import os
import subprocess
import sys
import time

print("[SETUP] === KHỞI ĐỘNG HỆ THỐNG MASTERBOT FILM AI ===")

def run_command(cmd, message):
    print(f"[SETUP] Đang thực hiện: {message}...")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[❌ FATAL ERROR] Thất bại tại bước: {message}. Lỗi: {e}")
        sys.exit(1)

# 1. Cập nhật hệ thống và cài đặt công cụ ép phim FFmpeg
run_command("apt-get update && apt-get install -y ffmpeg curl", "Cài đặt FFmpeg và công cụ hệ thống")

# 2. Nâng cấp PIP và cài đặt các thư viện kết nối cơ bản
libraries = "flask requests google-api-python-client google-auth-httplib2 google-auth-oauthlib"
run_command(f"pip install --upgrade pip && pip install {libraries}", "Cài đặt các thư viện Python (Flask, Requests, Drive API)")

# 3. Cài đặt AI Giọng nói Kokoro TTS chạy Offline trực tiếp trên GPU
run_command("pip install kokoro-tts soundfile", "Cài đặt AI giọng nói Kokoro TTS")

# 4. Tải file main.py từ kho GitHub Public của bạn về máy ảo Vast.ai
GITHUB_MAIN_URL = "https://raw.githubusercontent.com/0hieutrung0-eng/Robot-vastai/main/main.py"
run_command(f"curl -s {GITHUB_MAIN_URL} -o /workspace/main.py", "Tải file xử lý chính main.py từ GitHub")

# Kiểm tra lại chắc chắn file main.py đã nằm trên ổ cứng máy ảo trước khi kích hoạt
if not os.path.exists("/workspace/main.py"):
    print("[❌ FATAL ERROR] Không tìm thấy file main.py sau khi tải. Hãy kiểm tra lại link GitHub!")
    sys.exit(1)

print("[SETUP ✔️] Môi trường máy chủ đã sẵn sàng 100%!")
print("[SETUP 🚀] Đang kích hoạt chạy ngầm hệ thống main.py...")

# 5. Kích hoạt chạy ngầm file main.py độc lập, giải phóng tiến trình setup
subprocess.Popen(["python3", "/workspace/main.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Chờ 2 giây để Flask kịp mở cổng lắng nghe thành công
time.sleep(2)
print("[SETUP ✔️] Robot đã mở cổng lắng nghe 8188 thành công. Đang đợi Make.com bắn phân cảnh!")
