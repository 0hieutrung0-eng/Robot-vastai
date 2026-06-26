import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.25
MAX_INSTANCES = 1   # CHỈ DUY NHẤT 1 MÁY

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
    except Exception as e:
        print(f"[ERROR] Lấy danh sách instances thất bại: {e}")
        return []

while True:
    instances = get_instances()
    running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() == "running")

    print(f"\n[CHECK] Running: {running_count} | Tổng máy: {len(instances)}")

    # Destroy máy lỗi hoặc máy thừa (giữ nghiêm ngặt chỉ 1 máy)
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        
        if status in ["error", "dead", "stopped", "failed"] or len(instances) > MAX_INSTANCES:
            print(f"   🗑️ Destroy máy {inst.get('gpu_name')} (ID: {inst_id}) - Status: {status}")
            try:
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            except:
                pass
            time.sleep(8)

    if running_count >= MAX_INSTANCES:
        print(f"[✅] Đã có đúng 1 máy đang chạy → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # Tìm và thuê máy mới
    print("[🔍] Đang tìm máy phù hợp...")

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
echo "=== OnStart $(date) ==="

apt-get update && apt-get install -y git python3-pip

git config --global credential.helper ''
git config --global --add safe.directory /app
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/true

echo "Đang clone repo..."
rm -rf /app 2>/dev/null || true

# Clone repo chính, nếu fail thì dùng repo test public
git clone --depth 1 https://github.com/gradients-io/scraper-agent.git /app || \
git clone --depth 1 https://github.com/grokmind/test-agent.git /app || \
(mkdir -p /app && echo 'print("Agent placeholder running")' > /app/main.py && echo "No repo found, using placeholder")

cd /app

if [ -f "requirements.txt" ]; then
    echo "Cài requirements..."
    pip install -r requirements.txt --no-cache-dir --quiet || echo "Pip install có lỗi, tiếp tục"
fi

export TOKEN="rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
echo "=== Agent Started $(date) ==="

nohup python3 main.py > agent.log 2>&1 &
echo "✅ Agent đã khởi động ngầm"

sleep infinity
"""

            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": onstart_cmd
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=70)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
            else:
                print(f"[❌] Thuê thất bại: {rent_resp.status_code}")
                print(rent_resp.text[:400])
    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(40)
