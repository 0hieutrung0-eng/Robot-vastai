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

print("[START] Robot - Onstart script đơn giản")

def get_running_count():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            count = len(r.json().get("instances", []))
            print(f"[API] Hiện có {count}/{MAX_INSTANCES} máy")
            return count
    except:
        pass
    return 0

while True:
    if get_running_count() >= MAX_INSTANCES:
        print(f"[✅] ĐÃ ĐỦ {MAX_INSTANCES} máy → Nghỉ 10 phút")
        time.sleep(600)
        continue

    print("[🔍] Đang tìm máy...")

    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"in": ["RTX 3090 Ti"]},
        "order": [["dph_total", "asc"]],
        "limit": 5
    }

    resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

    if resp.status_code == 200 and resp.json().get("offers"):
        best = resp.json()["offers"][0]
        offer_id = best["id"]
        gpu = best.get("gpu_name")

        print(f"[🎯] Tìm thấy {gpu} → Thuê...")

        # Onstart script đơn giản, dùng một dòng
        rent_payload = {
            "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
            "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
            "disk": 40.0,
            "runtype": "args",
            "onstart": "apt-get update && apt-get install -y git python3-pip && git clone https://github.com/gradients-io/scraper-agent.git /app && cd /app && pip install -r requirements.txt --no-cache-dir && nohup python3 main.py > agent.log 2>&1 & echo 'Agent started' && tail -f agent.log"
        }

        rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=40)

        if rent_resp.status_code in (200, 201):
            print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
            time.sleep(900)
        else:
            print(f"[X] Thuê thất bại: {rent_resp.status_code}")
    else:
        print("[X] Chưa tìm thấy máy")
        time.sleep(60)

    time.sleep(30)
