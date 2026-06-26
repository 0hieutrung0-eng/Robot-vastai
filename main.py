import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.23
MAX_INSTANCES = 1   # Thay thành 2 nếu bạn muốn chạy 2 máy

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print(f"[START] Robot chống thuê lặp - Max {MAX_INSTANCES} máy")

def count_running_instances():
    try:
        resp = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            count = len(resp.json().get("instances", []))
            print(f"[INSTANCES] Hiện đang chạy: {count}/{MAX_INSTANCES} máy")
            return count
    except Exception as e:
        print(f"[WARN] Lỗi kiểm tra instances: {e}")
    return 0

while True:
    running = count_running_instances()

    if running >= MAX_INSTANCES:
        print(f"[✅] ĐÃ ĐỦ {MAX_INSTANCES} máy → Nghỉ 12 phút")
        time.sleep(720)
        continue

    print(f"[🔍] Hiện có {running} máy → Tiếp tục tìm...")

    # Tìm máy
    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "reliability": {"gte": 0.92},
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
        price = best.get("dph_total")

        print(f"[🎯] Tìm thấy {gpu} - ${price}/h → Thuê...")

        rent_payload = {
            "image": "vastai/base-image:cuda-12.8.1-cudnn-devel-ubuntu22.04",
            "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
            "disk": 40.0,
            "runtype": "args"
        }

        rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=30)

        if rent_resp.status_code in (200, 201):
            print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
            print("[⏳] Nghỉ 15 phút sau khi thuê thành công...")
            time.sleep(900)        # Nghỉ dài sau khi thuê
        else:
            print(f"[X] Thuê thất bại: {rent_resp.status_code}")
            time.sleep(30)
    else:
        print("[X] Chưa tìm thấy máy phù hợp")
        time.sleep(60)

    time.sleep(30)
