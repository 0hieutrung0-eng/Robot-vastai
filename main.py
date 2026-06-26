import os
import requests
import time
import json

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.18

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print("[START] Robot săn 3090 - Fix Image Gradients")

while True:
    try:
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

            print(f"[🎯] Tìm thấy {gpu} - ${price}/h → Đang thuê...")

            rent_payload = {
                "image": "vastai/base-image:cuda-12.4",   # ← Image công khai ổn định
                # Hoặc thử: "pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime"
                "env": {
                    "TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
                },
                "disk": 40.0,
                "runtype": "args",
                "onstart": "apt-get update && apt-get install -y git && git clone https://github.com/gradients-io/scraper-agent.git /app && cd /app && pip install -r requirements.txt && python main.py"  # Tùy chỉnh nếu cần
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=30)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}! Instance ID sẽ xuất hiện trong Vast.ai")
                time.sleep(900)
            else:
                print(f"[X] Thuê thất bại: {rent_resp.text[:200]}")
        else:
            print(f"[X] Chưa tìm thấy 3090 phù hợp")

    except Exception as e:
        print(f"[Lỗi] {e}")

    time.sleep(120)
