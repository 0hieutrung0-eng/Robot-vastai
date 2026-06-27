import os
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

# ========================== ONSTART ==========================
def create_onstart_script():
    AUTH_URL = f"https://{AGENT_TOKEN}@github.com{GITHUB_REPO}"
    return f"""#!/bin/bash
echo "=== OnStart Started $(date) ===" > /root/agent.log
set -e

apt-get update && apt-get install -y git python3-pip curl
pip install vastai

vastai set api-key {VAST_API_KEY} >> /root/agent.log 2>&1

echo "Vast CLI installed" >> /root/agent.log

git config --global credential.helper ''
git config --global --add safe.directory /app
rm -rf /app
if git clone --depth 1 {AUTH_URL} /app; then
    echo "→ Clone OK" >> /root/agent.log
else
    echo "→ Clone FAIL" >> /root/agent.log && exit 1
fi

cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q

export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
echo "→ Agent started" >> /root/agent.log
sleep infinity
"""

# ========================== SEARCH BẰNG CLI ==========================
def search_offers():
    try:
        print_and_log("[TRY] Tìm máy bằng Vast CLI...")
        
        # Kiểm tra vastai có sẵn không
        subprocess.run(["which", "vastai"], capture_output=True)
        
        cmd = [
            'vastai', 'search', 'offers',
            f'gpu_name=RTX_3090 verified=true rentable=true dph_total<={MAX_PRICE}',
            '--limit', '5', '--raw'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        
        print_and_log(f"[CLI] Return code: {result.returncode}")
        print_and_log(f"[CLI] Output: {result.stdout[:800]}")
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            try:
                offers = json.loads(result.stdout)
                if isinstance(offers, list) and len(offers) > 0:
                    print_and_log(f"[✅] Tìm thấy {len(offers)} máy!")
                    return offers
            except:
                pass
        return []
    except Exception as e:
        print_and_log(f"[ERROR] Vast CLI: {e}")
        return []

# ========================== MAIN ==========================
print_and_log("[🚀] Robot Vast.ai v3.0 - Vast CLI")

while True:
    active_count = 0
    print_and_log(f"[CHECK] Đang hoạt động: {active_count}/{MAX_INSTANCES}")

    offers = search_offers()
    if not offers:
        time.sleep(60)
        continue

    offers.sort(key=lambda x: float(x.get("dph_total", 999)))
    best = offers[0]
    print_and_log(f"[🎯] Thuê máy ID {best.get('id')} - ${best.get('dph_total')}/h")

    time.sleep(900)  # Chờ và thử lại sau
