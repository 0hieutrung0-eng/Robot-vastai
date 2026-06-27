import os
import requests
import time
import json
import threading
from fastapi import FastAPI
import uvicorn

app = FastAPI()
SYSTEM_STATUS = "Robot vừa khởi động..."

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

# ========================== CONFIG ==========================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

MAX_PRICE = 0.25      # $/giờ
MAX_INSTANCES = 1
GITHUB_REPO = "/0hieutrung0-eng/Robot-vastai.git"

BASE_URL = "https://console.vast.ai/api/v1"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

if not VAST_API_KEY or not AGENT_TOKEN:
    print_and_log("[❌] Thiếu VAST_API_KEY hoặc AGENT_TOKEN!")
    while True:
        time.sleep(3600)

# ========================== ONSTART SCRIPT ==========================
def create_onstart_script():
    AUTH_URL = f"https://{AGENT_TOKEN}@github.com{GITHUB_REPO}"
    return f"""#!/bin/bash
echo "=== Agent OnStart Started - $(date) ===" > /root/agent.log
set -e

apt-get update && apt-get install -y git python3-pip curl htop

git config --global credential.helper ''
git config --global --add safe.directory /app

rm -rf /app
if git clone --depth 1 {AUTH_URL} /app; then
    echo "→ Clone thành công" >> /root/agent.log
else
    echo "→ Clone thất bại" >> /root/agent.log
    exit 1
fi

cd /app
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --no-cache-dir -q
fi

export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
echo "→ Main agent started" >> /root/agent.log
sleep infinity
"""

# ========================== API HELPERS ==========================
def get_my_instances():
    try:
        r = requests.get(
            f"{BASE_URL}/instances/?owner=me",
            headers=HEADERS,
            params={"api_key": VAST_API_KEY},
            timeout=20
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("instances", []) if isinstance(data, dict) else []
        return []
    except Exception as e:
        print_and_log(f"[ERROR] get_my_instances: {e}")
        return []

def search_offers():
    query = {
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},   # Có thể thêm GPU khác
        "dph_total": {"lte": MAX_PRICE},
        "type": {"eq": "on-demand"}   # hoặc "interruptible" nếu muốn rẻ hơn
    }

    try:
        r = requests.post(
            f"{BASE_URL}/offers/search/",
            headers=HEADERS,
            params={"api_key": VAST_API_KEY},
            json=query,
            timeout=25
        )

        if r.status_code == 200:
            data = r.json()
            offers = data.get("offers", [])
            print_and_log(f"[📊] Tìm thấy {len(offers)} offer phù hợp")
            return offers
        else:
            print_and_log(f"[❌] Search failed: {r.status_code}")
            print(r.text[:500])
            return []
    except Exception as e:
        print_and_log(f"[ERROR] search_offers: {e}")
        return []

# ========================== MAIN LOOP ==========================
print_and_log("[START] Robot Vast.ai v2 - Tối ưu API 2026")

while True:
    instances = get_my_instances()
    active_count = sum(1 for inst in instances 
                      if inst.get("status") in ["running", "loading", "creating", "starting"])

    print_and_log(f"[CHECK] Đang chạy: {active_count}/{MAX_INSTANCES} | Tổng: {len(instances)}")

    # Cleanup máy lỗi / dư
    for inst in instances:
        status = str(inst.get("status", "")).lower()
        inst_id = inst.get("id")
        if status in ["error", "dead", "stopped", "failed"]:
            print_and_log(f"🗑️ Xóa máy lỗi: {inst.get('gpu_name')} (ID: {inst_id})")
            requests.delete(
                f"{BASE_URL}/instances/{inst_id}/",
                headers=HEADERS,
                params={"api_key": VAST_API_KEY}
            )
            time.sleep(8)

    if active_count >= MAX_INSTANCES:
        print_and_log(f"[✅] Đã đủ {active_count} máy. Nghỉ 8 phút...")
        time.sleep(480)
        continue

    # Tìm máy mới
    offers = search_offers()
    if not offers:
        print_and_log("[⏳] Không tìm thấy máy phù hợp, chờ 30s...")
        time.sleep(30)
        continue

    # Chọn máy rẻ nhất
    offers.sort(key=lambda x: float(x.get("dph_total", 999)))
    best = offers[0]
    price = float(best.get("dph_total", 0))

    print_and_log(f"[🎯] Thuê máy tốt nhất: {best.get('gpu_name')} - ${price}/h (Offer ID: {best['id']})")

    rent_payload = {
        "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",   # Cập nhật version mới hơn
        "disk": 50.0,
        "runtype": "ssh_direct",
        "onstart": create_onstart_script(),
        "ssh": True,
        "direct": True
    }

    rent_resp = requests.post(
        f"{BASE_URL}/asks/{best['id']}/",
        headers=HEADERS,
        params={"api_key": VAST_API_KEY},
        json=rent_payload,
        timeout=60
    )

    if rent_resp.status_code in (200, 201):
        print_and_log(f"[🎉] THUÊ THÀNH CÔNG! Chờ 15 phút để máy boot...")
        time.sleep(900)
    else:
        print_and_log(f"[❌] Thuê thất bại: {rent_resp.status_code}")
        print(rent_resp.text[:400])
        time.sleep(30)
