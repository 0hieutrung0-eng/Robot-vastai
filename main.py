import os
import requests
import time

# ====================== CẤU HÌNH ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.28          # Tăng nhẹ để dễ tìm máy hơn
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
            instances = r.json().get("instances", [])
            print(f"[DEBUG] Tìm thấy {len(instances)} instances từ API")
            return instances
        else:
            print(f"[ERROR] API instances: {r.status_code} - {r.text[:400]}")
            return []
    except Exception as e:
        print(f"[ERROR] Lấy instances: {e}")
        return []

def create_onstart_script():
    return f"""#!/bin/bash
echo "=== Agent OnStart Started - $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
echo "[1/3] Cloning repo..." >> /root/agent.log
rm -rf /app
if git clone --depth 1 {GITHUB_REPO} /app; then
    echo "→ Clone OK" >> /root/agent.log
else
    echo "→ Clone fail, placeholder" >> /root/agent.log
    mkdir -p /app
    echo 'import time; print("Placeholder..."); time.sleep(999999)' > /app/main.py
fi
cd /app
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --no-cache-dir -q >> /root/agent.log 2>&1
fi
echo "[3/3] Starting agent..." >> /root/agent.log
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > /root/agent.log 2>&1 &
echo "✅ Agent started - $(date)" >> /root/agent.log
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
        gpu = inst.get("gpu_name", "Unknown")

        if status in ["error", "dead", "stopped", "failed"]:
            print(f"   🗑️ Xóa máy lỗi: {gpu} (ID: {inst_id})")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)

        elif status in ACTIVE_STATUS:
            valid_kept += 1
            if valid_kept > MAX_INSTANCES:
                print(f"   🗑️ Xóa máy thừa: {gpu} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)

    if valid_kept >= MAX_INSTANCES:
        print(f"[✅] Đã có {valid_kept} máy ổn định → Nghỉ 8 phút")
        time.sleep(480)
        continue

    print("[🔍] Đang tìm máy RTX 3090...")

    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"in": ["RTX 3090 Ti", "RTX 3090"]},
        "order": [["dph_total", "asc"]],
        "limit": 8
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=20)
        offers = resp.json().get("offers", []) if resp.status_code == 200 else []

        if offers:
            best = offers[0]
            offer_id = best["id"]
            gpu = best.get("gpu_name")
            price = best.get("dph_total")

            print(f"[🎯] Tìm thấy {gpu} - ${price}/h → Thuê...")

            rent_payload = {
                "image": "nvidia/cuda:11.7.1-runtime-ubuntu22.04",
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": create_onstart_script()
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=90)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
            else:
                print(f"[❌] Thuê thất bại: {rent_resp.status_code}")
        else:
            print("[⚠️] Hiện không có máy 3090 nào dưới giá cho phép.")
    except Exception as e:
        print(f"[ERROR] Tìm/thuê máy: {e}")

    time.sleep(60)   # Tăng thời gian nghỉ giữa các lần quét
