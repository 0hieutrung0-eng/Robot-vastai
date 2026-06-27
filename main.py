import os
import requests
import time
import json
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

# ====================== CẤU HÌNH ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1
BASE_URL = "https://console.vast.ai/api/v0"   # Giữ v0 vì đang hoạt động

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

GITHUB_REPO = "https://github.com/0hieutrung0-eng/Robot-vastai.git"  # Sửa lại repo của bạn

print("[START] Robot Vast.ai v3.0 - Đang chạy")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/?owner=me", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
        else:
            print(f"[ERROR] Instances: {r.status_code}")
            return []
    except Exception as e:
        print(f"[ERROR] get_instances: {e}")
        return []

def create_onstart_script():
    return f"""#!/bin/bash
echo "=== OnStart Started - $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
git config --global credential.helper ''
git config --global --add safe.directory /app
rm -rf /app
if git clone --depth 1 {GITHUB_REPO} /app; then
    echo "→ Clone OK" >> /root/agent.log
else
    echo "→ Clone FAIL" >> /root/agent.log
fi
cd /app
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --no-cache-dir -q
fi
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
sleep infinity
"""

while True:
    instances = get_instances()
    running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() in {"running", "loading", "creating", "starting"})

    print(f"[CHECK] Running: {running_count}/{MAX_INSTANCES} | Total: {len(instances)}")

    # Cleanup máy lỗi / thừa
    for inst in instances:
        status = str(inst.get("status", "")).lower()
        inst_id = inst.get("id")
        if status in ["error", "dead", "stopped", "failed"]:
            print(f"🗑️ Xóa máy lỗi ID: {inst_id}")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)

    if running_count >= MAX_INSTANCES:
        print("[✅] Đủ máy → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # Tìm và thuê
    print("[🔍] Đang tìm RTX 3090...")
    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},
        "limit": 5
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=25)
        
        if resp.status_code == 200:
            offers = resp.json().get("offers", [])
            if offers:
                offers.sort(key=lambda x: float(x.get("dph_total", 999)))
                best = offers[0]
                print(f"[🎯] Thuê {best.get('gpu_name')} - ${best.get('dph_total')}/h")

                rent_payload = {
                    "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                    "disk": 50.0,
                    "runtype": "ssh_direct",
                    "onstart": create_onstart_script()
                }

                rent_resp = requests.put(f"{BASE_URL}/asks/{best['id']}/", headers=HEADERS, json=rent_payload, timeout=90)
                
                if rent_resp.status_code in (200, 201):
                    print("[🎉] THUÊ THÀNH CÔNG!")
                    time.sleep(900)
                else:
                    print(f"[❌] Thuê thất bại: {rent_resp.status_code}")
            else:
                print("[⚠️] Không có máy phù hợp")
        else:
            print(f"[ERROR] Search: {resp.status_code} - {resp.text[:300]}")
    except Exception as e:
        print(f"[ERROR] Main loop: {e}")

    time.sleep(40)
