import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.25
MAX_INSTANCES = 1   # Chỉ giữ tối đa 1 máy

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print("[START] Robot Vast.ai - Chỉ thuê tối đa 1 GPU")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
    except:
        pass
    return []

def is_running(inst):
    """Chỉ tính là running khi máy thực sự hoạt động"""
    status = str(inst.get("status", "")).lower()
    if status == "running":
        return True
    # Đang creating/starting thì chưa tính là running
    return False

while True:
    instances = get_instances()
    
    # Đếm số máy thực sự đang chạy
    running_count = sum(1 for inst in instances if is_running(inst))
    
    print(f"[CHECK] Máy thực sự đang chạy: {running_count}/{MAX_INSTANCES}")

    # === Destroy máy lỗi hoặc không chạy được ===
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        gpu = inst.get("gpu_name", "Unknown")

        if any(x in status for x in ["error", "failed", "crashed", "not running"]):
            print(f"[🗑️] Destroy máy lỗi/không chạy: {gpu} (ID: {inst_id}) - Status: {status}")
            try:
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS)
            except:
                pass
            time.sleep(20)

    # Nếu đã đủ 1 máy đang chạy thật thì nghỉ
    if running_count >= MAX_INSTANCES:
        print(f"[✅] Đã đủ {MAX_INSTANCES} máy đang chạy → Nghỉ 10 phút")
        time.sleep(600)
        continue

    # === Tìm và thuê máy mới ===
    print("[🔍] Đang tìm máy RTX 3090 series...")

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
            gpu = best.get("gpu_name", "Unknown")

            print(f"[🎯] Tìm thấy {gpu} → Thuê...")

            onstart_cmd = """set -e
echo "=== OnStart bắt đầu $(date) ==="
apt-get update && apt-get install -y git python3-pip
git clone https://github.com/gradients-io/scraper-agent.git /app
cd /app
pip install -r requirements.txt --no-cache-dir
export TOKEN="rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
echo "=== Agent Started $(date) ==="
nohup python3 main.py > agent.log 2>&1 &
sleep infinity"""

            rent_payload = {
                "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": onstart_cmd
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=45)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)   # Chờ 15 phút
            else:
                print(f"[❌] Thuê thất bại: {rent_resp.status_code}")
                print(rent_resp.text[:400])
                time.sleep(60)
        else:
            print("[😴] Không tìm thấy máy phù hợp")
            time.sleep(60)

    except Exception as e:
        print(f"[ERROR] {e}")
        time.sleep(60)

    time.sleep(30)
