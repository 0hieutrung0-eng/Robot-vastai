import requests
import time
import json

# ====================== CẤU HÌNH ======================
VAST_API_KEY = "fdf12c0dad8dc53d40e18bd0ebfd39834f46944396b697e4d173a1418476f219"
MAX_PRICE = 0.15          # $/giờ
MIN_RELIABILITY = 0.90
MIN_INET_DOWN = 600
MIN_CUDA = 11.8

BASE_URL = "https://console.vast.ai/api/v0"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {VAST_API_KEY}"
}

print("[START] Robot săn GPU Vast.ai 24/7 - Phiên bản 2026 ✅")

while True:
    try:
        print(f"\n[INFO] Quét lúc {time.strftime('%X')}...")

        # ================== 1. TÌM MÁY ==================
        search_payload = {
            "type": "on-demand",           # hoặc "bid" nếu muốn rẻ hơn
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "verified": {"eq": True},
            "reliability": {"gte": MIN_RELIABILITY},
            "inet_down": {"gte": MIN_INET_DOWN},
            "cuda_max_good": {"gte": MIN_CUDA},
            "dph_total": {"lte": MAX_PRICE},   # quan trọng nhất
            "order": [["dph_total", "asc"]],   # rẻ nhất trước
            "limit": 5
        }

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload)

        if resp.status_code != 200:
            print(f"[X] Lỗi API {resp.status_code}: {resp.text[:200]}")
            time.sleep(60)
            continue

        offers = resp.json().get("offers", [])

        if not offers:
            print("[X] Chưa có máy nào dưới giá trần.")
        else:
            best = offers[0]
            offer_id = best["id"]
            price = best.get("dph_total") or best.get("rentprice")
            gpu = best.get("gpu_name", "Unknown")

            print(f"[🎯] Tìm thấy! {gpu} - ${price}/h - ID: {offer_id}")
            print(f"    Reliability: {best.get('reliability')}, Inet: {best.get('inet_down')} MB/s")

            # ================== 2. THUÊ MÁY ==================
            rent_payload = {
                "image": "gradients/scraper-agent:latest",
                "env": {
                    "TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
                },
                "disk": 10.0,
                "runtype": "args"          # giữ nguyên như code cũ của bạn
            }

            rent_resp = requests.put(
                f"{BASE_URL}/asks/{offer_id}/",
                headers=HEADERS,
                json=rent_payload
            )

            if rent_resp.status_code in (200, 201):
                data = rent_resp.json()
                instance_id = data.get("new_contract")
                print(f"[🎉] THUÊ THÀNH CÔNG! Instance ID: {instance_id}")
                # Có thể break hoặc continue tùy bạn muốn thuê nhiều máy
            else:
                print(f"[X] Thuê thất bại {rent_resp.status_code}: {rent_resp.text[:150]}")

    except Exception as e:
        print(f"[💥] Lỗi: {e}")

    time.sleep(300)  # 5 phút
