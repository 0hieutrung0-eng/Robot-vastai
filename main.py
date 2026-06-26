import os
import requests
import time
import json

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.19
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print(f"[START] Robot săn 3090 - Giới hạn {MAX_INSTANCES} máy (Fix offer expired)")

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
            print("[⏸] Đủ máy → Nghỉ 5 phút")
            time.sleep(300)
            continue

        # Tìm offer
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "reliability": {"gte": 0.92},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},
            "order": [["dph_total", "asc"]],
            "limit": 10
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

        if resp.status_code == 200 and resp.json().get("offers"):
            best = resp.json()["offers"][0]
            offer_id = best["id"]
            price = best.get("dph_total")
            gpu = best.get("gpu_name")

            print(f"[🎯] Tìm thấy {gpu} - ${price}/h (ID: {offer_id}) → Đang thử thuê...")

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
                error_msg = rent_resp.text[:200]
                print(f"[X] Thuê thất bại: {rent_resp.status_code} - {error_msg}")
                if "no_such_ask" in error_msg or "not available" in error_msg:
                    print("[!] Offer đã bị lấy mất → tiếp tục quét ngay")
        else:
            print(f"[X] Chưa tìm thấy 3090 phù hợp")

    except Exception as e:
        print(f"[💥] Lỗi: {e}")

    time.sleep(90)   # Quét nhanh hơn một chút
