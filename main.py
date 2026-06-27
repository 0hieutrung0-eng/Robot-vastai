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

# ====================== CONFIG ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

MAX_PRICE = 0.23
MAX_INSTANCES = 1
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

def create_onstart_script():
    return f"""#!/bin/bash
echo "OnStart Started $(date)" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
git config --global credential.helper ''
rm -rf /app
git clone --depth 1 {GITHUB_REPO} /app
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
sleep infinity
"""

print_and_log("[🚀] Robot Vast.ai - Stable Version")

while True:
    try:
        # Tìm máy
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},
            "limit": 8
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=25)
        print_and_log(f"[SEARCH] Status: {resp.status_code}")

        if resp.status_code == 200:
            offers = resp.json().get("offers", [])
            print_and_log(f"[✅] Tìm thấy {len(offers)} offer")

            if offers:
                # Chọn rẻ nhất
                best = min(offers, key=lambda x: float(x.get("dph_total", 999)))
                price = float(best.get("dph_total", 0))
                offer_id = best["id"]

                print_and_log(f"[🎯] Thử thuê {best.get('gpu_name')} - ${price} (ID: {offer_id})")

                rent_payload = {
                    "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                    "disk": 40,
                    "runtype": "ssh_direct",
                    "onstart": create_onstart_script()
                }

                rent_resp = requests.put(
                    f"{BASE_URL}/asks/{offer_id}/",
                    headers=HEADERS,
                    json=rent_payload,
                    timeout=90
                )

                if rent_resp.status_code in (200, 201):
                    print_and_log(f"[🎉] THUÊ THÀNH CÔNG! ID: {offer_id}")
                    time.sleep(900)
                else:
                    print_and_log(f"[❌] Thuê thất bại: {rent_resp.status_code}")
                    print_and_log(f"Chi tiết: {rent_resp.text[:400]}")
        else:
            print_and_log(f"[ERROR] Search: {resp.status_code}")

    except Exception as e:
        print_and_log(f"[ERROR] {e}")

    time.sleep(50)
