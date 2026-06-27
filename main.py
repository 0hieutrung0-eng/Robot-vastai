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
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# Chạy web server để giữ Spaces alive
def run_web_server():
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

threading.Thread(target=run_web_server, daemon=True).start()

# ====================== CONFIG ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1
BASE_URL = "https://console.vast.ai/api/v0"

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

GITHUB_REPO = "https://github.com/0hieutrung0-eng/Robot-vastai.git"   # ← SỬA LẠI

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

if not VAST_API_KEY or not AGENT_TOKEN:
    print_and_log("[❌] THIẾU VAST_API_KEY hoặc AGENT_TOKEN!")
    while True:
        time.sleep(3600)

def create_onstart_script():
    return f"""#!/bin/bash
echo "=== OnStart Started $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
git config --global credential.helper ''
git config --global --add safe.directory /app
rm -rf /app
git clone --depth 1 {GITHUB_REPO} /app
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
sleep infinity
"""

# ====================== MAIN LOOP ======================
print_and_log("[🚀] Robot Vast.ai - Hugging Face Version")

while True:
    try:
        # Lấy instances
        r = requests.get(f"{BASE_URL}/instances/?owner=me", headers=HEADERS, timeout=15)
        instances = r.json().get("instances", []) if r.status_code == 200 else []

        running_count = sum(1 for inst in instances if str(inst.get("status","")).lower() in ["running","loading","creating","starting"])

        print_and_log(f"[CHECK] Running: {running_count}/{MAX_INSTANCES}")

        # Cleanup
        for inst in instances:
            status = str(inst.get("status","")).lower()
            inst_id = inst.get("id")
            if status in ["error","dead","stopped","failed"] or running_count > MAX_INSTANCES:
                print_and_log(f"🗑️ Xóa máy: {inst.get('gpu_name')} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)
                running_count -= 1

        if running_count >= MAX_INSTANCES:
            time.sleep(480)
            continue

        # Tìm máy
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},
            "limit": 5
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=20)

        if resp.status_code == 200:
            offers = resp.json().get("offers", [])
            if offers:
                best = min(offers, key=lambda x: float(x.get("dph_total", 999)))
                print_and_log(f"[🎯] Thuê {best.get('gpu_name')} - ${best.get('dph_total')}/h")

                rent_payload = {
                    "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                    "disk": 50,
                    "runtype": "ssh_direct",
                    "onstart": create_onstart_script()
                }

                rent_resp = requests.put(f"{BASE_URL}/asks/{best['id']}/", headers=HEADERS, json=rent_payload, timeout=60)

                if rent_resp.status_code in (200, 201):
                    print_and_log("[🎉] THUÊ THÀNH CÔNG!")
                    time.sleep(900)
                else:
                    print(f"[❌] Thuê lỗi: {rent_resp.status_code}")
            else:
                print("[⚠️] Không có máy phù hợp")
        else:
            print(f"[ERROR] Search: {resp.status_code}")

    except Exception as e:
        print(f"[ERROR] Loop: {e}")

    time.sleep(40)
