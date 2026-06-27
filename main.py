import os
import requests
import time
import threading
import subprocess
from fastapi import FastAPI
import uvicorn

app = FastAPI()
SYSTEM_STATUS = "Robot đang khởi động..."

@app.get("/")
def read_root():
    return {"status": "active", "message": SYSTEM_STATUS, "time": time.strftime("%Y-%m-%d %H:%M:%S")}

def run_web_server():
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

threading.Thread(target=run_web_server, daemon=True).start()

# ========================== CONFIG ==========================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1
GITHUB_REPO = "/0hieutrung0-eng/Robot-vastai.git"

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

if not VAST_API_KEY or not AGENT_TOKEN:
    print_and_log("[❌] Thiếu API key!")
    while True: time.sleep(3600)

# ========================== ONSTART (Cài Vast CLI) ==========================
def create_onstart_script():
    AUTH_URL = f"https://{AGENT_TOKEN}@github.com{GITHUB_REPO}"
    return f"""#!/bin/bash
echo "=== OnStart Started $(date) ===" > /root/agent.log
set -e

apt-get update && apt-get install -y git python3-pip curl
pip install vastai

vastai set api-key {VAST_API_KEY}

git config --global credential.helper ''
git config --global --add safe.directory /app
rm -rf /app
git clone --depth 1 {AUTH_URL} /app && echo "→ Clone OK" >> /root/agent.log || echo "→ Clone FAIL" >> /root/agent.log

cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q

export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
echo "→ Agent started with Vast CLI" >> /root/agent.log
sleep infinity
"""

# ========================== SEARCH BẰNG CLI ==========================
def search_offers():
    try:
        print_and_log("[TRY] Tìm máy RTX 3090 bằng Vast CLI...")
        cmd = f'vastai search offers "gpu_name=RTX_3090 verified=true rentable=true dph_total<={MAX_PRICE} type=on-demand" --limit 5 --raw'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            offers = json.loads(result.stdout)
            if isinstance(offers, list) and offers:
                print_and_log(f"[✅] Tìm thấy {len(offers)} offer!")
                return offers
        print_and_log(f"[CLI] Output: {result.stdout[:300]}")
    except Exception as e:
        print_and_log(f"[ERROR] Vast CLI: {e}")
    return []

# ========================== MAIN ==========================
print_and_log("[🚀] Robot Vast.ai v2.8 - Using Vast CLI")

while True:
    # Giả sử lấy instances (có thể cải tiến sau)
    active_count = 0
    print_and_log(f"[CHECK] Đang hoạt động: {active_count}/{MAX_INSTANCES}")

    offers = search_offers()
    if not offers:
        time.sleep(60)
        continue

    # Chọn rẻ nhất
    offers.sort(key=lambda x: float(x.get("dph_total", 999)))
    best = offers[0]
    print_and_log(f"[🎯] Thuê máy: {best.get('gpu_name')} - ${best.get('dph_total')}/h")

    # Rent bằng CLI
    try:
        rent_cmd = f"vastai create instance {best['id']} --image nvidia/cuda:12.4.1-runtime-ubuntu22.04 --disk 50 --onstart '{create_onstart_script()}' --ssh --direct"
        subprocess.run(rent_cmd, shell=True, timeout=60)
        print_and_log("[🎉] Đã gửi lệnh thuê!")
        time.sleep(900)
    except Exception as e:
        print_and_log(f"[ERROR] Rent: {e}")
        time.sleep(60)
