import os
import requests
import time

# ====================== CẤU HÌNH ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.28          # Tăng nhẹ để dễ tìm
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

# ================== SỬA REPO Ở ĐÂY ==================
GITHUB_REPO = "https://github.com/YOUR_USERNAME/YOUR_REPO.git"

print("[START] Robot Vast.ai - Giữ DUY NHẤT 1 GPU")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            instances = r.json().get("instances", [])
            print(f"[DEBUG] API trả về {len(instances)} instances")
            return instances
        else:
            print(f"[ERROR] API instances: {r.status_code} - {r.text[:300]}")
            return []
    except Exception as e:
        print(f"[ERROR] Lấy instances: {e}")
        return []

def create_onstart_script():
    return f"""#!/bin/bash
echo "=== OnStart Started $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
rm -rf /app
if git clone --depth 1 {GITHUB_REPO} /app; then
    echo "→ Clone thành công" >> /root/agent.log
else
    echo "→ Clone thất bại, dùng placeholder" >> /root/agent.log
    mkdir -p /app
    echo 'import time; print("Placeholder running..."); time.sleep(999999)' > /app/main.py
fi
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q >> /root/agent.log 2>&1
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
        gpu = inst.get("gpu_name", "Unknown")

        if status in ["error", "dead", "stopped", "failed"]:
            print(f"   🗑️ Xóa máy lỗi: {gpu} (ID: {inst_id})")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)
        elif status in ACTIVE_STATUS:
            valid_kept += 1
            if valid_kept > MAX_INSTANCES:
                print(f"   🗑️ Xóa máy thừa: {gpu}")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)

    if valid_kept >= MAX_INSTANCES:
        print(f"[✅] Đã có {valid_kept} máy ổn định → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # ====================== TÌM MÁY ======================
    print("[🔍] Đang tìm RTX 3090...")

    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"contains": "3090"},   # Dùng contains thay vì in
        "order": [["dph_total", "asc"]],
        "limit": 10
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=20)
        
        if resp.status_code != 200:
            print(f"[ERROR] Search API: {resp.status_code} - {resp.text[:200]}")
        else:
            offers = resp.json().get("offers", [])
            print(f"[DEBUG] Tìm thấy {len(offers)} offer phù hợp")

            if offers:
                best = offers[0]
                offer_id = best["id"]
                gpu = best.get("gpu_name", "Unknown")
                price = best.get("dph_total", 0)

                print(f"[🎯] Thuê {gpu} - ${price}/h")

                rent_payload = {
                    "image": "nvidia/cuda:11.7.1-runtime-ubuntu22.04",   # Đã đổi theo yêu cầu
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
                print("[⚠️] Không tìm thấy máy 3090 nào dưới giá. Thử lại sau...")

    except Exception as e:
        print(f"[ERROR] Lỗi tìm/thuê: {e}")

    time.sleep(50)
