import os
import requests
import time
import json
import threading
from fastapi import FastAPI
import uvicorn

# ==============================================================================
# PHẦN 1: KHỞI TẠO MÁY CHỦ WEB BẮT BUỘC ĐỂ GIỮ HUGGING FACE SPACES LUÔN "RUNNING"
# ==============================================================================
app = FastAPI()
SYSTEM_STATUS = "Robot đang chuẩn bị kiểm tra cấu trúc API..."

@app.get("/")
def read_root():
    return {
        "status": "active",
        "robot_log": SYSTEM_STATUS,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def run_web_server():
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

threading.Thread(target=run_web_server, daemon=True).start()


# ====================== CẤU HÌNH HỆ THỐNG VÀ KEY XÁC THỰC ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

BASE_URL = "https://console.vast.ai/api/v1"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

print_and_log("[START] Robot Vast.ai v1 - Chế Độ Nội Soi & Chẩn Đoán Cấu Trúc API")

if not VAST_API_KEY:
    print_and_log("[❌] LỖI CẤU HÌNH: Thiếu VAST_API_KEY!")
    while True:
        time.sleep(3600)


# ==============================================================================
# PHẦN 2: VÒNG LẶP NỘI SOI - THỬ NGHIỆM VÀ ĐỌC LỖI TỪ VAST.AI
# ==============================================================================
while True:
    print_and_log("\n" + "="*60)
    print_and_log("[🔍] BẮT ĐẦU QUÁ TRÌNH NỘI SOI ENDPOINT THỊ TRƯỜNG...")
    print_and_log("="*60)

    # Thử nghiệm endpoint cơ bản nhất không kèm bộ lọc để ép Server trả về cấu trúc gốc
    test_urls = [
        {"name": "Endpoint /instances/", "url": f"{BASE_URL}/instances/?api_key={VAST_API_KEY}"},
        {"name": "Endpoint /bundles/", "url": f"{BASE_URL}/bundles/?api_key={VAST_API_KEY}"},
        {"name": "Endpoint /users/current/", "url": f"{BASE_URL}/users/current/?api_key={VAST_API_KEY}"}
    ]

    for target in test_urls:
        print_and_log(f"\n📡 Đang gửi request test tới: {target['name']}")
        try:
            # Gửi request GET đơn giản
            r = requests.get(target['url'], headers=HEADERS, timeout=15)
            
            print_and_log(f"  -> HTTP Status Code: {r.status_code}")
            print_and_log(f"  -> Nội dung Server trả về thô:")
            print(f"{r.text}", flush=True)
            
        except Exception as e:
            print_and_log(f"  -> Lỗi kết nối vật lý: {e}")

    print_and_log("\n------------------------------------------------------------")
    print_and_log("[💡] Đã quét xong 1 lượt chẩn đoán. Đợi 45 giây để reset và quét lại...")
    time.sleep(45)
