import os
import requests
import time
import json

# ====================== DEBUG API KEY ======================
VAST_API_KEY = os.getenv("VAST_API_KEY")

print(f"[DEBUG] VAST_API_KEY length = {len(VAST_API_KEY) if VAST_API_KEY else 0}")
if not VAST_API_KEY:
    print("[ERROR] KHÔNG TÌM THẤY VAST_API_KEY! Hãy set Environment Variable.")
    time.sleep(10)

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {VAST_API_KEY}"
}

print("[START] Robot săn GPU Vast.ai 24/7 - Phiên bản Debug 2026")

while True:
    try:
        print(f"\n[INFO] Quét lúc {time.strftime('%X')}...")

        # Test API Key trước khi search
        test_resp = requests.get(f"{BASE_URL}/instances/", headers=HEADERS)
        if test_resp.status_code == 401:
            print("[ERROR] API Key vẫn không hợp lệ!")
            print(test_resp.json())
            time.sleep(60)
            continue

        # Search offers
        search_payload = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "reliability": {"gte": 0.90},
            "inet_down": {"gte": 600},
            "cuda_max_good": {"gte": 11.8},
            "dph_total": {"lte": 0.15},
            "order": [["dph_total", "asc"]],
            "limit": 5
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload)

        if resp.status_code == 200:
            offers = resp.json().get("offers", [])
            if offers:
                best = offers[0]
                print(f"[🎯] Tìm thấy máy: {best.get('gpu_name')} - ${best.get('dph_total')}/h")
                # ... (phần thuê máy giữ nguyên như trước)
            else:
                print("[X] Chưa có máy nào dưới 0.15$/h")
        else:
            print(f"[X] Lỗi search: {resp.status_code} - {resp.text[:150]}")

    except Exception as e:
        print(f"[💥] Lỗi: {e}")

    time.sleep(300)
