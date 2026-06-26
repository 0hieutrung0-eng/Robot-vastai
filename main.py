import os
import requests
import time
import json

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.15
MAX_INSTANCES = 1   # Giới hạn chỉ 1 máy

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print(f"[START] Robot săn 3090 - Giới hạn {MAX_INSTANCES} máy")

def get_running_instances():
    try:
        resp = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return len(resp.json().get("instances", []))
    except:
        pass
    return 0

while True:
    try:
        running = get_running_instances()
        print(f"[INFO] Đang chạy: {running}/{MAX_INSTANCES} máy | {time.strftime('%X')}")

        if running >= MAX_INSTANCES:
            print("[⏸] Đã đủ máy, chờ...")
            time.sleep(300)
            continue

        # Tìm máy
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "reliability": {"gte": 0.92},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},
            "order": [["dph_total", "asc"]],
            "limit": 5
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

        if resp.status_code == 200 and resp.json().get("offers"):
            best = resp.json()["offers"][0]
            offer_id = best["id"]
            price = best.get("dph_total")
            gpu = best.get("gpu_name")

            print(f"[🎯] Tìm thấy {gpu} - ${price}/h → Thuê...")

            rent_payload = {
                "image": "vastai/base-image:cuda-12.8.1-cudnn-devel-ubuntu22.04",  # Tag đúng
                "env": {
                    "TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
                },
                "disk": 40.0,
                "runtype": "args",
                "onstart": """#!/bin/bash
echo "=== Starting Gradients Agent ==="
apt-get update && apt-get install -y git python3-pip
git clone https://github.com/gradients-io/scraper-agent.git /app || echo "Clone failed"
cd /app && pip install -r requirements.txt || echo "Pip failed"
python3 main.py || echo "Run failed - check TOKEN"
"""
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=30)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
            else:
                print(f"[X] Thuê thất bại: {rent_resp.text[:150]}")
        else:
            print(f"[X] Chưa tìm thấy 3090 dưới ${MAX_PRICE}")

    except Exception as e:
        print(f"[Lỗi] {e}")

    time.sleep(120)
