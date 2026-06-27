import os
import requests
import time
import threading
from fastapi import FastAPI
import uvicorn

app = FastAPI()
SYSTEM_STATUS = "Robot đang chạy..."

@app.get("/")
def read_root():
    return {"status": "active", "message": SYSTEM_STATUS, "time": time.strftime("%Y-%m-%d %H:%M:%S")}

def run_web_server():
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

threading.Thread(target=run_web_server, daemon=True).start()

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

MAX_PRICE = 0.22
BASE_URL = "https://console.vast.ai/api/v0"

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

GITHUB_REPO = "https://github.com/0hieutrung0-eng/Robot-vastai.git"

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

print_and_log("[🚀] Robot Vast.ai - New API Key")

while True:
    try:
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},
            "limit": 6
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=25)
        print_and_log(f"[SEARCH] Status: {resp.status_code}")

        if resp.status_code == 200:
            offers = resp.json().get("offers", [])
            if offers:
                best = min(offers, key=lambda x: float(x.get("dph_total", 999)))
                print_and_log(f"[🎯] Tìm thấy {best.get('gpu_name')} - ${best.get('dph_total')}")
                # Thêm phần thuê ở đây nếu muốn
            else:
                print_and_log("[⚠️] Không có máy phù hợp")
        elif resp.status_code == 403:
            print_and_log("[⏳] 403 - Nghỉ 10 phút...")
            time.sleep(600)
        else:
            print_and_log(f"[ERROR] {resp.status_code}")
    except Exception as e:
        print_and_log(f"[ERROR] {e}")

    time.sleep(80)
