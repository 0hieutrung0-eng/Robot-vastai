import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.23
MAX_INSTANCES = 1   # Chỉ thuê tối đa 1 máy (Sửa thành 2 nếu muốn chạy 2 máy)

BASE_URL = "https://vast.ai"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print(f"[START] Robot kiểm soát chặt - Max {MAX_INSTANCES} máy")

def get_running_count():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            # Lọc chỉ đếm các máy ở trạng thái đang chạy hoặc đang thiết lập (tránh đếm sót máy đang tạo)
            instances = r.json().get("instances", [])
            count = len(instances)
            print(f"[API] Hiện có {count}/{MAX_INSTANCES} máy trong tài khoản")
            return count, True
    except Exception as e:
        print(f"[API Error] Lỗi kết nối: {e}")
    return 0, False # Trả về False để biết API lỗi, không nên đoán bừa số lượng bằng 0

while True:
    # 1. KIỂM TRA TRƯỚC SỐ LƯỢNG MÁY ĐANG CHẠY
    running, success = get_running_count()

    if not success:
        print("[⚠️] Lỗi gọi API kiểm tra máy. Thử lại sau 60 giây để an toàn...")
        time.sleep(60)
        continue

    if running >= MAX_INSTANCES:
        print(f"[✅] ĐÃ ĐỦ SỐ MÁY ({running}/{MAX_INSTANCES}) → KHÔNG THUÊ THÊM. Nghỉ 5 phút...")
        time.sleep(300) # Nghỉ 5 phút rồi kiểm tra lại xem máy có bị sập không
        continue       # BẮT BUỘC: Quay lại đầu vòng lặp, bỏ qua toàn bộ logic thuê máy phía dưới

    # 2. CHƯA ĐỦ MÁY → TIẾN HÀNH TÌM OFFER
    print(f"[🔍] Chưa đủ máy ({running}/{MAX_INSTANCES}), đang tìm offer...")

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

            print(f"[🎯] Tìm thấy {gpu} → Đang thuê...")

            # 3. TIẾN HÀNH THUÊ VÀ CHẠY BOT (Đã sửa lỗi treo tail -f)
            rent_payload = {
                "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args",
                "onstart": """#!/bin/bash
echo "=== GRADIENTS AGENT START ==="
apt-get update && apt-get install -y git python3-pip
git clone https://github.com /app
cd /app
pip install -r requirements.txt --no-cache-dir || echo "Pip failed"
echo "Running agent..."
nohup python3 main.py > agent.log 2>&1 &
echo "Agent started at $(date)"
"""
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=35)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}! Đợi 3 phút để máy khởi động hẳn...")
                time.sleep(180) # Giảm thời gian chờ xuống 3 phút để kiểm tra lại trạng thái sớm hơn
            else:
                print(f"[X] Thuê thất bại (Code: {rent_resp.status_code})")
                time.sleep(30)
        else:
            print("[X] Chưa tìm thấy máy phù hợp. Tìm lại sau 30 giây...")
            time.sleep(30)
            
    except Exception as e:
        print(f"[X] Lỗi trong quá trình tìm/thuê: {e}")
        time.sleep(30)
