import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.25
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print("[START] Robot Vast.ai - Phiên bản ổn định nhất")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        return r.json().get("instances", []) if r.status_code == 200 else []
    except:
        return []

while True:
    instances = get_instances()
    running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() == "running")

    print(f"\n[CHECK] Máy đang chạy tốt: {running_count}/{MAX_INSTANCES}")

    # Destroy máy lỗi / kẹt
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        if status != "running":
            print(f"   🗑️ Destroy máy kẹt: {inst.get('gpu_name')} (ID: {inst_id})")
            try:
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS)
            except:
                pass
            time.sleep(15)

    if running_count >= MAX_INSTANCES:
        print("[✅] Đủ máy → Nghỉ 10 phút")
        time.sleep(600)
        continue

    print("[🔍] Tìm máy RTX 3090...")

    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"in": ["RTX 3090 Ti", "RTX 3090"]},
        "order": [["dph_total", "asc"]],
        "limit": 5
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)
        offers = resp.json().get("offers", []) if resp.status_code == 200 else []

        if offers:
            best = offers[0]
            offer_id = best["id"]
            gpu = best.get("gpu_name")

            print(f"[🎯] Tìm thấy {gpu} → Thuê...")

            # ===================== ONSTART SẠCH =====================
            onstart_cmd = r"""set -e
echo "=== OnStart bắt đầu $(date) ==="

apt-get update && apt-get install -y git python3-pip

git config --global credential.helper ''
git config --global --add safe.directory /app

echo "Đang clone repository..."
git clone --depth 1 https://github.com/gradients-io/scraper-agent.git /app

cd /app
echo "Cài requirements..."
pip install -r requirements.txt --no-cache-dir --quiet

export TOKEN="rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
echo "=== Agent Started $(date) ==="

nohup python3 main.py > agent.log 2>&1 &
echo "✅ Agent đang chạy nền - Kiểm tra bằng: tail -f agent.log"

sleep infinity
"""

            rent_payload = {
                "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": onstart_cmd
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=60)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
            else:
                print(f"[❌] Thuê thất bại: {rent_resp.status_code}")
                print(rent_resp.text[:500])
                time.sleep(60)
    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(40)
