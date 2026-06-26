import os
import requests
import time
import json

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.23
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

print(f"[START] Robot debug API - Max {MAX_INSTANCES} máy")
print(f"[DEBUG] VAST_API_KEY length = {len(VAST_API_KEY)}")

def test_api_key():
    try:
        r = requests.get(f"{BASE_URL}/users/current/", headers=HEADERS, timeout=15)
        print(f"[TEST KEY] Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"[✅] API Key HỢP LỆ! User: {data.get('email')}")
            return True
        else:
            print(f"[❌] API Key lỗi: {r.text[:300]}")
            return False
    except Exception as e:
        print(f"[❌] Lỗi kết nối: {e}")
        return False

# Test key lần đầu
if not test_api_key():
    print("[💥] API Key không hoạt động. Kiểm tra Environment Variable!")
    time.sleep(30)

def get_running_count():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        print(f"[API instances] Status: {r.status_code}")
        if r.status_code == 200:
            count = len(r.json().get("instances", []))
            print(f"[API] Hiện có {count}/{MAX_INSTANCES} máy")
            return count
        else:
            print(f"[API Error] {r.text[:200]}")
            return 0
    except Exception as e:
        print(f"[API Exception] {e}")
        return 0

while True:
    running = get_running_count()

    if running >= MAX_INSTANCES:
        print(f"[✅] ĐÃ ĐỦ {MAX_INSTANCES} máy → Nghỉ 10 phút")
        time.sleep(600)
        continue

    print(f"[🔍] Chưa đủ máy, đang tìm...")

    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"in": ["RTX 3090 Ti"]},
        "order": [["dph_total", "asc"]],
        "limit": 5
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

        if resp.status_code == 200 and resp.json().get("offers"):
            best = resp.json()["offers"][0]
            offer_id = best["id"]
            gpu = best.get("gpu_name")

            print(f"[🎯] Tìm thấy {gpu} → Thuê...")

            rent_payload = {
                "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args"
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=35)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}!")
                time.sleep(900)
            else:
                print(f"[X] Thuê thất bại: {rent_resp.status_code}")
        else:
            print(f"[X] Chưa tìm thấy máy (Status: {resp.status_code})")
    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(60)
