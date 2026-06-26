import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.15
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {"Authorization": f"Bearer {VAST_API_KEY}", "Content-Type": "application/json"}

print("[START] Robot săn GPU + Chạy Gradients Agent")

def count_running():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=10)
        return len(r.json().get("instances", [])) if r.status_code == 200 else 0
    except:
        return 0

while True:
    try:
        if count_running() >= MAX_INSTANCES:
            print("[OK] Đang chạy đủ máy → Nghỉ")
            time.sleep(600)
            continue

        # Tìm máy
        search = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json={
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090 Ti", "RTX 3090"]},
            "order": [["dph_total", "asc"]],
            "limit": 5
        }, timeout=15)

        if search.status_code == 200 and search.json().get("offers"):
            best = search.json()["offers"][0]
            offer_id = best["id"]
            gpu = best.get("gpu_name")

            print(f"[🎯] Tìm thấy {gpu} → Đang thuê...")

            rent_payload = {
                "image": "vastai/base-image:cuda-12.8.1-cudnn-devel-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args",
                "onstart": """#!/bin/bash
echo "=== GRADIENTS AGENT STARTING ==="
apt-get update && apt-get install -y git python3-pip
git clone https://github.com/gradients-io/scraper-agent.git /app
cd /app
pip install -r requirements.txt
echo "Running Gradients Agent..."
python3 main.py > /app/agent.log 2>&1 &
echo "Agent started at $(date)" >> /app/agent.log
tail -f /app/agent.log
"""
            }

            rent = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=30)
            if rent.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
    except Exception as e:
        print(f"Lỗi: {e}")

    time.sleep(120)
