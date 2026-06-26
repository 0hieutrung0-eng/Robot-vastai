import os
import requests
import time
import json

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.15
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print("[START] Robot săn 3090 / 3090 Ti - Phiên bản ổn định")

def get_running_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return len(r.json().get("instances", []))
    except:
        pass
    return 0

while True:
    try:
        running = get_running_instances()
        print(f"[INFO] Đang chạy: {running}/{MAX_INSTANCES} máy | {time.strftime('%X')}")

        if running >= MAX_INSTANCES:
            print("[✅] Đã đủ máy → Nghỉ dài")
            time.sleep(600)   # 10 phút
            continue

        # Ưu tiên 3090 Ti trước, sau đó mới 3090
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "reliability": {"gte": 0.92},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090 Ti", "RTX 3090"]},
            "order": [["dph_total", "asc"]],
            "limit": 10
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

        if resp.status_code == 200 and resp.json().get("offers"):
            best = resp.json()["offers"][0]
            offer_id = best["id"]
            price = best.get("dph_total")
            gpu = best.get("gpu_name")

            print(f"[🎯] Tìm thấy {gpu} - ${price}/h → Thuê...")

            rent_payload = {
                "image": "vastai/base-image:cuda-12.8.1-cudnn-devel-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args"
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=25)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
            else:
                print(f"[X] Thuê thất bại")
        else:
            print("[X] Chưa tìm thấy máy phù hợp")

    except Exception as e:
        print(f"[Lỗi] {e}")

    time.sleep(120)
