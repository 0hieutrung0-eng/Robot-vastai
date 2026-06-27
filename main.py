import os
import requests
import time

# ====================== CẤU HÌNH ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

GITHUB_REPO = "https://github.com/YOUR_USERNAME/YOUR_REPO.git"   # ← SỬA LẠI

print("[START] Robot Vast.ai - Giữ DUY NHẤT 1 GPU")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
        else:
            print(f"[ERROR] API: {r.status_code} - {r.text[:300]}")
            return []
    except Exception as e:
        print(f"[ERROR] Lấy instances: {e}")
        return []

def create_onstart_script():
    return f"""#!/bin/bash
echo "=== OnStart Started $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
rm -rf /app
git clone --depth 1 {GITHUB_REPO} /app || {{
    mkdir -p /app
    echo 'import time; print("Placeholder"); time.sleep(999999)' > /app/main.py
}}
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > /root/agent.log 2>&1 &
echo "✅ Agent started $(date)" >> /root/agent.log
tail -f /dev/null
"""

while True:
    instances = get_instances()
    ACTIVE_STATUS = {"running", "loading", "creating", "starting"}
    
    running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() in ACTIVE_STATUS)
    print(f"\n[CHECK] Running: {running_count} | Total: {len(instances)}")

    valid_kept = 0
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        gpu_name = inst.get("gpu_name", "Unknown")

        if status in ["error", "dead", "stopped", "failed"]:
            print(f"   🗑️ Xóa máy lỗi: {gpu_name} (ID: {inst_id})")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)
        elif status in ACTIVE_STATUS:
            valid_kept += 1
            if valid_kept > MAX_INSTANCES:
                print(f"   🗑️ Xóa máy thừa: {gpu_name}")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)

    if valid_kept >= MAX_INSTANCES:
        print(f"[✅] Đã có máy ổn định → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # ====================== TÌM MÁY - FILTER ĐÃ NỚI RỘNG ======================
    print("[🔍] Đang tìm máy RTX 3090...")

    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti", "3090"]},  # Nới rộng
        "order": [["dph_total", "asc"]],
        "limit": 10
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=20)
        offers = resp.json().get("offers", []) if resp.status_code == 200 else []

        print(f"[DEBUG] Tìm thấy {len(offers)} offer")

        if offers:
            best = offers[0]
            offer_id = best["id"]
            gpu = best.get("gpu_name", "Unknown")
            price = best.get("dph_total", 0)

            print(f"[🎯] Tìm thấy {gpu} - ${price}/h → Thuê...")

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
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
            else:
                print(f"[❌] Thuê thất bại: {rent_resp.status_code}")
        else:
            print("[⚠️] Vẫn không tìm thấy offer. Thử lại sau...")

    except Exception as e:
        print(f"[ERROR] Tìm/thuê: {e}")

    time.sleep(45)
