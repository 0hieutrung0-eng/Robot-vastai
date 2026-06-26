import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.23
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print("[START] Robot thông minh - Tự destroy máy lỗi")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
    except:
        pass
    return []

while True:
    instances = get_instances()
    running = len(instances)
    print(f"[CHECK] Hiện có {running}/{MAX_INSTANCES} máy")

    # Kiểm tra máy lỗi
    for inst in instances:
        inst_id = inst.get("id")
        status = inst.get("status", "")
        gpu = inst.get("gpu_name", "Unknown")
        
        if "error" in status.lower() or "failed" in status.lower():
            print(f"[🗑️] Phát hiện máy lỗi {gpu} (ID: {inst_id}) → Destroy...")
            try:
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS)
                print(f"[OK] Đã destroy máy lỗi {inst_id}")
            except:
                pass
            time.sleep(30)

    if running >= MAX_INSTANCES:
        print(f"[✅] Đủ máy → Nghỉ 10 phút")
        time.sleep(600)
        continue

    # Tìm và thuê máy mới
    print("[🔍] Đang tìm máy...")

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

        if resp.status_code == 200 and resp.json().get("offers"):
            best = resp.json()["offers"][0]
            offer_id = best["id"]
            gpu = best.get("gpu_name")

            print(f"[🎯] Tìm thấy {gpu} → Thuê...")

            rent_payload = {
                "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args",
                "onstart": "apt-get update && apt-get install -y git python3-pip && git clone https://github.com/gradients-io/scraper-agent.git /app && cd /app && pip install -r requirements.txt --no-cache-dir && nohup python3 main.py > agent.log 2>&1 & echo 'Agent started'"
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=40)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
            else:
                print(f"[X] Thuê thất bại")
                time.sleep(40)
    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(60)
