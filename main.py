import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.23
MAX_INSTANCES = 1   # Đổi thành 2 nếu bạn muốn chạy 2 máy

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print(f"[START] Robot kiểm soát chặt - Max {MAX_INSTANCES} máy")

def get_running_count():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            count = len(r.json().get("instances", []))
            print(f"[API] Hiện có {count}/{MAX_INSTANCES} máy đang chạy")
            return count
    except Exception as e:
        print(f"[API Error] {e}")
    return 0

while True:
    running = get_running_count()

    if running >= MAX_INSTANCES:
        print(f"[✅] ĐÃ ĐỦ MÁY → Nghỉ 12 phút")
        time.sleep(720)
        continue

    print(f"[🔍] Chưa đủ máy, đang tìm offer...")

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

        print(f"[🎯] Tìm thấy {gpu} → Đang thuê...")

        rent_payload = {
            "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
            "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
            "disk": 40.0,
            "runtype": "args",
            "onstart": """#!/bin/bash
echo "=== GRADIENTS AGENT START ==="
apt-get update && apt-get install -y git python3-pip
git clone https://github.com/gradients-io/scraper-agent.git /app
cd /app
pip install -r requirements.txt --no-cache-dir || echo "Pip failed"
echo "Running agent..."
python3 main.py > agent.log 2>&1 &
echo "Agent started at $(date)"
tail -f agent.log
"""
        }

        rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=35)

        if rent_resp.status_code in (200, 201):
            print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
            time.sleep(900)
        else:
            print(f"[X] Thuê thất bại")
            time.sleep(40)
    else:
        print("[X] Chưa tìm thấy máy phù hợp")
        time.sleep(60)

    time.sleep(30)
