import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.25
MAX_INSTANCES = 1   # Chỉ duy nhất 1 máy

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print("[START] Robot Vast.ai - Chỉ giữ DUY NHẤT 1 GPU")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        return r.json().get("instances", []) if r.status_code == 200 else []
    except:
        return []

while True:
    instances = get_instances()
    running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() == "running")

    print(f"\n[CHECK] Số máy đang chạy: {running_count}")

    # === Destroy tất cả máy thừa hoặc lỗi ===
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        gpu = inst.get("gpu_name", "Unknown")

        # Destroy nếu là máy lỗi hoặc nếu đang có nhiều hơn 1 máy
        if status != "running" or len(instances) > MAX_INSTANCES:
            print(f"   🗑️ Destroy: {gpu} (ID: {inst_id}) - Status: {status}")
            try:
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS)
            except:
                pass
            time.sleep(12)

    # Nếu đã có đúng 1 máy chạy tốt thì nghỉ
    if running_count >= MAX_INSTANCES:
        print("[✅] Đã có đúng 1 máy đang chạy → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # Tìm và thuê máy mới
    print("[🔍] Đang tìm máy RTX 3090...")

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

            onstart_cmd = """set -e
echo "=== OnStart bắt đầu $(date) ==="

apt-get update && apt-get install -y git python3-pip

git config --global credential.helper ''
git config --global --add safe.directory /app
unset GIT_ASKPASS

echo "Đang clone..."
git clone --depth 1 https://github.com/gradients-io/scraper-agent.git /app || git clone https://github.com/gradients-io/scraper-agent.git /app

cd /app
echo "Cài requirements..."
pip install -r requirements.txt --no-cache-dir --quiet

export TOKEN="rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
echo "=== Agent Started $(date) ==="

nohup python3 main.py > agent.log 2>&1 &
echo "✅ Agent đang chạy nền"

sleep infinity
"""

            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
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
                time.sleep(30)
    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(40)
