import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.15
MAX_INSTANCES = 1   # CHỈ 1 MÁY

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print("[START] Robot 3090 Ti - Giới hạn CHẮC CHẮN 1 máy")

def count_running_instances():
    try:
        resp = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            instances = resp.json().get("instances", [])
            count = len(instances)
            print(f"[CHECK] Hiện có {count} máy đang chạy:")
            for i in instances:
                print(f"   • {i.get('gpu_name')} (ID: {i.get('id')}) - Status: {i.get('status')}")
            return count
    except:
        pass
    return 0

while True:
    try:
        running = count_running_instances()
        
        if running >= MAX_INSTANCES:
            print(f"[✅] ĐÃ ĐỦ {MAX_INSTANCES} máy → Nghỉ 10 phút")
            time.sleep(600)
            continue

        # Tìm máy (ưu tiên 3090 Ti)
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "reliability": {"gte": 0.92},
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090 Ti"]},
            "order": [["dph_total", "asc"]],
            "limit": 10
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

        if resp.status_code == 200 and resp.json().get("offers"):
            best = resp.json()["offers"][0]
            offer_id = best["id"]
            gpu = best.get("gpu_name")
            price = best.get("dph_total")

            print(f"[🎯] Tìm thấy {gpu} - ${price}/h → Đang thuê...")

            rent_payload = {
                "image": "vastai/base-image:cuda-12.8.1-cudnn-devel-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args"
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=30)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)  # Nghỉ lâu sau khi thuê
            else:
                print(f"[X] Thuê thất bại: {rent_resp.status_code}")
        else:
            print("[X] Chưa tìm thấy máy phù hợp")

    except Exception as e:
        print(f"[Lỗi] {e}")

    time.sleep(90)
