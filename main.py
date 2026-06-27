import os
import requests
import time
import threading
from fastapi import FastAPI
import uvicorn

app = FastAPI()
SYSTEM_STATUS = "Robot đang khởi động..."

@app.get("/")
def read_root():
    return {
        "status": "active",
        "message": SYSTEM_STATUS,
        "env_check": "VAST_API_KEY exists" if os.getenv("VAST_API_KEY") else "MISSING KEY!"
    }

def run_web_server():
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

threading.Thread(target=run_web_server, daemon=True).start()

# ====================== DEBUG ENV ======================
print("=== ENVIRONMENT DEBUG ===")
print("VAST_API_KEY exists:", bool(os.getenv("VAST_API_KEY")))
print("VAST_API_KEY length:", len(os.getenv("VAST_API_KEY", "")))
print("AGENT_TOKEN exists:", bool(os.getenv("AGENT_TOKEN")))
print("=========================")

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

if not VAST_API_KEY:
    print_and_log = lambda x: print(x, flush=True)
    print_and_log("[❌] VAST_API_KEY KHÔNG TỒN TẠI trên HF Spaces!")
    while True:
        time.sleep(3600)

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

GITHUB_REPO = "https://github.com/0hieutrung0-eng/Robot-vastai.git"  # Sửa nếu cần

print_and_log("[🚀] Robot Vast.ai - HF Spaces Debug Version")

while True:
    try:
        # Test API Key
        test = requests.get(f"{BASE_URL}/instances/?owner=me", headers=HEADERS, timeout=15)
        print_and_log(f"[TEST] API Key: {test.status_code}")

        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "dph_total": {"lte": 0.25},
            "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},
            "limit": 5
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=20)
        print_and_log(f"[SEARCH] Status: {resp.status_code}")

        if resp.status_code == 200:
            offers = resp.json().get("offers", [])
            print_and_log(f"[✅] Tìm thấy {len(offers)} offer")
            if offers:
                best = min(offers, key=lambda x: float(x.get("dph_total", 999)))
                print_and_log(f"[🎯] Thuê {best.get('gpu_name')} - ${best.get('dph_total')}")
                # Thêm logic thuê ở đây nếu muốn
        else:
            print_and_log(f"[ERROR] Response: {resp.text[:400]}")

    except Exception as e:
        print_and_log(f"[ERROR] {e}")

    time.sleep(60)
