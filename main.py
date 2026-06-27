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
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def run_web_server():
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

threading.Thread(target=run_web_server, daemon=True).start()

# ========================== CONFIG ==========================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1
GITHUB_REPO = "/0hieutrung0-eng/Robot-vastai.git"

BASE_URL = "https://console.vast.ai/api/v1"

def get_auth_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {VAST_API_KEY}"
    }

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

if not VAST_API_KEY or not AGENT_TOKEN:
    print_and_log("[❌] Thiếu VAST_API_KEY hoặc AGENT_TOKEN!")
    while True: time.sleep(3600)

# ========================== ONSTART ==========================
def create_onstart_script():
    AUTH_URL = f"https://{AGENT_TOKEN}@github.com{GITHUB_REPO}"
    return f"""#!/bin/bash
echo "=== OnStart Started $(date) ===" > /root/agent.log
set -e
apt-get update && apt-get install -y git python3-pip curl htop
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
echo "→ Main agent started" >> /root/agent.log
sleep infinity
"""

# ========================== API ==========================
def get_my_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/?owner=me", headers=get_auth_headers(), timeout=20)
        return r.json().get("instances", []) if r.status_code == 200 else []
    except Exception as e:
        print_and_log(f"[ERROR] get_my_instances: {e}")
        return []

def search_offers():
    # Query theo kiểu string (cách CLI dùng)
    query_str = "verified=true rentable=true gpu_name=RTX_3090 dph_total<=0.25 type=on-demand limit=10"
    
    try:
        print_and_log("[TRY] Tìm máy RTX 3090...")
        r = requests.get(
            f"{BASE_URL}/instances/search/",
            headers=get_auth_headers(),
            params={"query": query_str},
            timeout=25
        )
        print_and_log(f"[DEBUG] Search status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            offers = data.get("offers") or data.get("instances") or data.get("results") or []
            print_and_log(f"[✅] Tìm thấy {len(offers)} offer!")
            return offers
        else:
            print_and_log(f"[❌] Search failed {r.status_code} - {r.text[:400]}")
            return []
    except Exception as e:
        print_and_log(f"[ERROR] search_offers: {e}")
        return []

# ========================== MAIN LOOP ==========================
print_and_log("[🚀] Robot Vast.ai v2.5 - Search fix")

while True:
    instances = get_my_instances()
    active_count = sum(1 for inst in instances if inst.get("status") in ["running", "loading", "creating", "starting"])
    print_and_log(f"[CHECK] Đang hoạt động: {active_count}/{MAX_INSTANCES}")

    for inst in instances:
        if str(inst.get("status", "")).lower() in ["error", "dead", "stopped", "failed"]:
            inst_id = inst.get("id")
            print_and_log(f"🗑️ Xóa máy lỗi ID: {inst_id}")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=get_auth_headers())
            time.sleep(8)

    if active_count >= MAX_INSTANCES:
        time.sleep(480)
        continue

    offers = search_offers()
    if not offers:
        time.sleep(40)
        continue

    offers.sort(key=lambda x: float(x.get("dph_total", 999)))
    best = offers[0]
    price = float(best.get("dph_total", 0))

    print_and_log(f"[🎯] Thuê máy: {best.get('gpu_name')} - ${price}/h")

    rent_payload = {
        "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
        "disk": 50,
        "onstart": create_onstart_script(),
        "runtype": "ssh_direct",
        "ssh": True,
        "direct": True
    }

    rent_resp = requests.put(
        f"{BASE_URL}/asks/{best['id']}/",
        headers=get_auth_headers(),
        json=rent_payload,
        timeout=60
    )

    if rent_resp.status_code in (200, 201):
        print_and_log("[🎉] THUÊ THÀNH CÔNG! Chờ boot...")
        time.sleep(900)
    else:
        print_and_log(f"[❌] Thuê thất bại: {rent_resp.status_code}")
        time.sleep(30)
