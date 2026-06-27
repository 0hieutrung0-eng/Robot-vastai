import os
import time
import threading
import subprocess
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

MAX_PRICE = 0.22
GITHUB_REPO = "https://github.com/0hieutrung0-eng/Robot-vastai.git"

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

if not VAST_API_KEY:
    print_and_log("[❌] Thiếu VAST_API_KEY!")
    while True: time.sleep(3600)

print_and_log("[🚀] Robot Vast.ai - Using Official CLI")

# ====================== ONSTART (Cài CLI) ======================
def create_onstart_script():
    return f"""#!/bin/bash
echo "=== OnStart Started $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
pip install --upgrade vastai
vastai set api-key {VAST_API_KEY}
git clone --depth 1 {GITHUB_REPO} /app
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
sleep infinity
"""

while True:
    try:
        print_and_log("[CLI] Đang tìm máy RTX 3090...")

        # Tìm máy
        cmd = f'vastai search offers "gpu_name=RTX_3090 verified=true rentable=true dph_total<={MAX_PRICE}" --limit 5 --raw'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            import json
            offers = json.loads(result.stdout)
            if offers:
                # Chọn rẻ nhất
                best = min(offers, key=lambda x: float(x.get("dph_total", 999)))
                print_and_log(f"[🎯] Tìm thấy {best.get('gpu_name')} - ${best.get('dph_total')} (ID: {best.get('id')})")

                # Thuê
                offer_id = best['id']
                rent_cmd = f"vastai create instance {offer_id} --image nvidia/cuda:12.4.1-runtime-ubuntu22.04 --disk 40 --ssh --direct --onstart '{create_onstart_script()}'"
                print_and_log("[CLI] Đang thuê máy...")
                rent_result = subprocess.run(rent_cmd, shell=True, capture_output=True, text=True, timeout=60)
                print_and_log(f"[RENT] {rent_result.stdout[:300]}")
                time.sleep(900)
            else:
                print_and_log("[⚠️] Không tìm thấy máy phù hợp")
        else:
            print_and_log(f"[CLI] Lỗi: {result.stderr[:200]}")
    except Exception as e:
        print_and_log(f"[ERROR] {e}")

    time.sleep(90)
