import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.23
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v0"

# Thêm User-Agent để bypass bộ lọc Cloudflare của Vast.ai
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

print("[START] Robot - Kiểm soát VGA chặt chẽ")

def get_running_count():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            count = len(r.json().get("instances", []))
            print(f"[API] Hiện có {count}/{MAX_INSTANCES} máy")
            return count, True # Trả về số lượng và xác nhận API chạy đúng
        else:
            print(f"[API Error] Thất bại, HTTP Code: {r.status_code}")
    except Exception as e:
        print(f"[API Error] Lỗi kết nối/JSON: {e}")
    return 0, False # API lỗi thì báo False để không xử lý bậy

while True:
    # 1. KIỂM TRA SỐ LƯỢNG MÁY TRƯỚC
    count, is_api_ok = get_running_count()
    
    if not is_api_ok:
        print("[⚠️] Không thể kiểm tra số máy do lỗi API. Thử lại sau 60 giây...")
        time.sleep(60)
        continue

    if count >= MAX_INSTANCES:
        print(f"[✅] ĐÃ THUÊ {count}/{MAX_INSTANCES} VGA ĐANG CHẠY → DỪNG THUÊ. Nghỉ 5 phút...")
        time.sleep(300)
        continue # Quay lại đầu vòng lặp, bỏ qua hoàn toàn đoạn code thuê máy bên dưới

    # 2. TIẾN HÀNH TÌM MÁY NẾU CHƯA CÓ VGA NÀO CHẠY
    print("[🔍] Đang tìm máy...")

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

            # XOÁ BỎ tail -f ở cuối để tránh treo tiến trình Vast.ai
            onstart_cmd = (
                "apt-get update && apt-get install -y git python3-pip && "
                "git clone https://github.com/gradients-io/scraper-agent.git /app && "
                "cd /app && pip install -r requirements.txt --no-cache-dir && "
                "nohup python3 main.py > agent.log 2>&1 & echo 'Agent started thành công'"
            )

            rent_payload = {
                "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args",
                "onstart": onstart_cmd
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=40)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}! Đợi 3 phút để kiểm tra lại trạng thái...")
                time.sleep(180) # Giảm sleep xuống 3 phút để bot cập nhật danh sách máy nhanh hơn
            else:
                print(f"[X] Thuê thất bại: {rent_resp.status_code}")
                time.sleep(30)
        else:
            print("[X] Chưa tìm thấy máy phù hợp")
            time.sleep(30)
            
    except Exception as e:
        print(f"[X] Lỗi hệ thống trong vòng lặp: {e}")
        time.sleep(30)
