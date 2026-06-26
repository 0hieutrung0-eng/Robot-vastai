import os
import requests
import time
import json

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.15   # Tăng nhẹ để dễ tìm 3090

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {"Authorization": f"Bearer {VAST_API_KEY}", "Content-Type": "application/json"}

print("[START] Robot săn 3090 cho Gradients.io")

while True:
    try:
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "reliability": {"gte": 0.92},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti", "RTX 4090"]},
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
                "image": "gradients/scraper-agent:latest",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 30.0,
                "runtype": "args"
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload)
            
            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}! Kiểm tra Gradients dashboard.")
                time.sleep(900)  # Nghỉ 15 phút sau khi thuê
            else:
                print("[X] Thuê thất bại:", rent_resp.text[:150])
        else:
            print(f"[X] Chưa có 3090/4090 dưới ${MAX_PRICE}")

    except Exception as e:
        print("[Lỗi]", e)

    time.sleep(120)  # Quét mỗi 2 phút
