import os
import requests
import time

# ====================== CẤU HÌNH ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.28
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

GITHUB_REPO = "https://github.com/YOUR_USERNAME/YOUR_REPO.git"   # ← SỬA

print("[START] Robot Vast.ai v3 - Fixed Search Endpoint")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            instances = r.json().get("instances", [])
            print(f"[DEBUG] Instances: {len(instances)}")
            return instances
        else:
            print(f"[ERROR] Instances API: {r.status_code}")
            return []
    except Exception as e:
        print(f"[ERROR] Get instances: {e}")
        return []

def create_onstart_script():
    return f"""#!/bin/bash
echo "=== OnStart $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip
rm -rf /app
git clone --depth 1 {GITHUB_REPO} /app || {{
    mkdir -p /app
    echo 'import time; print("Placeholder"); time.sleep(999999)' > /app/main.py
}}
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > /root/agent.log 2>&1 &
echo "✅ Agent started" >> /root/agent.log
tail -f /dev/null
"""

while True:
    instances = get_instances()
    
    ACTIVE_STATUS = {"running", "loading", "creating", "starting"}
    running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() in ACTIVE_STATUS)

    print(f"[CHECK] Running: {running_count} | Total: {len(instances)}")

    valid_kept = 0
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        if status in ["error", "dead", "stopped", "failed"]:
            print(f"   🗑️ Xóa máy lỗi ID: {inst_id}")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)
        elif status in ACTIVE_STATUS:
            valid_kept += 1
            if valid_kept > MAX_INSTANCES:
                print(f"   🗑️ Xóa máy thừa ID: {inst_id}")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)

    if valid_kept >= MAX_INSTANCES:
        print("[✅] Đã có máy → Nghỉ")
        time.sleep(480)
        continue

    # ====================== TÌM MÁY - ENDPOINT MỚI ======================
    print("[🔍] Đang tìm RTX 3090...")

    search_payload = {
        "type": "on-demand",           # Thêm type
        "rentable": True,
        "rented": False,
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"contains": "3090"},
        "order": ["dph_total", "asc"],
        "limit": 10
    }

    try:
        # Thử nhiều endpoint khác nhau
        endpoints = [
            f"{BASE_URL}/bundles/search",
            f"{BASE_URL}/search",
            f"{BASE_URL}/offers",
            f"{BASE_URL}/bundles"
        ]

        offers = []
        for url in endpoints:
            print(f"[DEBUG] Thử endpoint: {url}")
            resp = requests.post(url, headers=HEADERS, json=search_payload, timeout=20)
            print(f"   → Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                offers = data.get("offers", []) if isinstance(data, dict) else []
                if offers:
                    print(f"[SUCCESS] Tìm thấy {len(offers)} offer!")
                    break

        if offers:
            best = offers[0]
            print(f"[🎯] Tìm thấy {best.get('gpu_name')} ${best.get('dph_total')}/h")
            # Bạn có thể uncomment phần thuê nếu muốn tự động thuê
        else:
            print("[⚠️] Không tìm thấy offer nào")

    except Exception as e:
        print(f"[ERROR] Search error: {e}")

    time.sleep(60)
