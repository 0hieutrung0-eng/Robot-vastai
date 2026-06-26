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

print(f"[START] Robot thông minh - Chỉ quét khi chưa đủ máy (max {MAX_INSTANCES} máy)")

def count_running_instances():
    try:
        resp = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            count = len(resp.json().get("instances", []))
            print(f"[CHECK] Hiện đang chạy: {count}/{MAX_INSTANCES} máy")
            return count
    except Exception as e:
        print(f"[WARN] Không kiểm tra được: {e}")
    return 0

while True:
    running = count_running_instances()

    if running >= MAX_INSTANCES:
        print(f"[✅] ĐÃ ĐỦ {MAX_INSTANCES} máy → Nghỉ 10 phút không quét")
        time.sleep(600)
        continue

    # ========== CHỈ QUÉT KHI CHƯA ĐỦ MÁY ==========
    print(f"[🔍] Chưa đủ máy ({running}/{MAX_INSTANCES}), đang quét offer...")

    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "reliability": {"gte": 0.92},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"in": ["RTX 3090 Ti"]},
        "order": [["dph_total", "asc"]],
        "limit": 8
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
            time.sleep(900)   # Nghỉ 15 phút sau khi thuê
        else:
            print(f"[X] Thuê thất bại")
            time.sleep(30)
    else:
        print("[X] Chưa có offer phù hợp")
        time.sleep(60)   # Nghỉ ngắn nếu chưa tìm thấy

    # Không sleep dài ở đây vì đã có logic kiểm tra ở đầu vòng lặp
