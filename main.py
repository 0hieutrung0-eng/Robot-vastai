import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.30
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

GITHUB_REPO = "https://github.com/YOUR_USERNAME/YOUR_REPO.git"   # ← SỬA LẠI

print("[START] Robot Vast.ai - Tự động thuê & thay thế GPU")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        return r.json().get("instances", []) if r.status_code == 200 else []
    except:
        return []

def create_onstart_script():
    return f"""#!/bin/bash
echo "=== OnStart $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip
rm -rf /app
git clone --depth 1 {GITHUB_REPO} /app || {{
    mkdir -p /app
    echo 'import time; [print("Running placeholder") for _ in range(999999)]' > /app/main.py
}}
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
echo "✅ Agent started" >> /root/agent.log
tail -f /dev/null
"""

while True:
    instances = get_instances()
    
    active_count = 0
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        gpu = inst.get("gpu_name", "Unknown")

        if status in ["error", "dead", "stopped", "failed"]:
            print(f"🗑️ Xóa máy lỗi: {gpu} (ID: {inst_id}) - Status: {status}")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(10)
        elif status in ["running", "loading", "creating", "starting"]:
            active_count += 1
            print(f"✅ Máy đang chạy: {gpu} (ID: {inst_id})")

    print(f"[STATUS] Số máy đang hoạt động: {active_count}")

    # Nếu chưa có máy nào chạy → Thuê mới
    if active_count < MAX_INSTANCES:
        print("[🔍] Không có máy nào chạy → Tìm và thuê mới...")

        search_payload = {
            "rentable": True,
            "rented": False,
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"contains": "3090"},
            "limit": 8
        }

        try:
            resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=20)
            
            if resp.status_code == 200:
                offers = resp.json().get("offers", [])
                if offers:
                    best = offers[0]
                    offer_id = best["id"]
                    gpu_name = best.get("gpu_name")
                    price = best.get("dph_total")

                    print(f"[🎯] Tìm thấy {gpu_name} - ${price}/h → Thuê...")

                    rent_payload = {
                        "image": "nvidia/cuda:11.7.1-runtime-ubuntu22.04",
                        "disk": 40.0,
                        "runtype": "ssh_direct",
                        "onstart": create_onstart_script()
                    }

                    rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", 
                                           headers=HEADERS, 
                                           json=rent_payload, 
                                           timeout=90)

                    if rent_resp.status_code in (200, 201):
                        print(f"[🎉] THUÊ THÀNH CÔNG {gpu_name}!")
                        time.sleep(900)  # Chờ 15 phút máy khởi động
                    else:
                        print(f"[❌] Thuê thất bại: {rent_resp.status_code}")
                else:
                    print("[⚠️] Không tìm thấy máy 3090 phù hợp")
            else:
                print(f"[ERROR] Search API: {resp.status_code}")
        except Exception as e:
            print(f"[ERROR] Lỗi tìm/thuê: {e}")
    else:
        print("[OK] Đã có máy chạy ổn định")

    time.sleep(60)
