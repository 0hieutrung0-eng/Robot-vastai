import os
import requests
import time

# GIỮ NGUYÊN KHÔNG THAY ĐỔI ENDPOINT GỐC
BASE_URL = "https://console.vast.ai/api/v1"

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.35    # ĐÃ TĂNG: Nâng lên 0.35$ để dễ khớp lệnh với thị trường RTX 3090
MAX_INSTANCES = 1   # Đổi thành 2 nếu muốn chạy nhiều máy

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print(f"[START] Robot quản lý thông minh - Max {MAX_INSTANCES} máy")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            instances = r.json().get("instances", [])
            print(f"[API] Hiện có {len(instances)} máy trong tài khoản")
            return instances, True
        else:
            print(f"[API Error] Status: {r.status_code}")
    except Exception as e:
        print(f"[API Exception] {e}")
    return [], False

while True:
    instances, is_api_ok = get_instances()
    
    if not is_api_ok:
        print("[⚠️] Không thể kết nối API Vast.ai để kiểm tra máy. Thử lại sau 60 giây...")
        time.sleep(60)
        continue
    
    # 1. XỬ LÝ VÀ DỌN DẸP MÁY LỖI
    healthy_count = 0
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        actual_status = str(inst.get("actual_status", "")).lower()
        gpu = inst.get("gpu_name", "Unknown")
        
        error_keywords = ["error", "failed", "storage", "oci", "daemon", "pull", "unsatisfied", "broken"]
        if any(kw in status or kw in actual_status for kw in error_keywords):
            print(f"[🗑️] Máy lỗi {gpu} (ID: {inst_id}) → Destroy...")
            try:
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                print(f"[OK] Destroy máy lỗi thành công")
            except Exception as e:
                print(f"[X] Lỗi gửi lệnh xóa: {e}")
            time.sleep(10)
        else:
            healthy_count += 1

    print(f"[CHECK] Số máy khỏe mạnh: {healthy_count}/{MAX_INSTANCES}")

    if healthy_count >= MAX_INSTANCES:
        print(f"[✅] ĐÃ ĐỦ MÁY → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # 2. TÌM VÀ THUÊ MÁY MỚI
    print("[🔍] Chưa đủ máy, đang tìm...")

    search_payload = {
        "q": {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "dph_total": {"lte": MAX_PRICE},
            # ĐÃ MỞ RỘNG: Thêm RTX 4070 Ti và 3080 Ti để tăng tốc độ tìm thấy máy
            "gpu_name": {"in": ["RTX 3090 Ti", "RTX 3090", "RTX 4070 Ti", "RTX 3080 Ti"]},
            # ĐÃ TỐI ƯU: Hạ xuống 535.00 để quét được nhiều máy giá rẻ hơn, CUDA 12.4 vẫn chạy tốt
            "driver_version": {"gte": 535.00}
        },
        "order": [["dph_total", "asc"]],
        "limit": 5
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

        if resp.status_code == 200:
            res_data = resp.json()
            # Xử lý bóc tách JSON linh hoạt tránh crash lỗi kiểu dữ liệu
            offers = res_data.get("offers", []) if isinstance(res_data, dict) else []
            
            if not offers and isinstance(res_data, list):
                offers = res_data

            if isinstance(offers, list) and len(offers) > 0:
                best = offers[0]
                offer_id = best["id"]
                gpu = best.get("gpu_name")
                price = best.get("dph_total")
                print(f"[🎯] Tìm thấy {gpu} (Giá: {price}$/h) (ID: {offer_id}) → Thuê...")
            else:
                print("[X] Chưa tìm thấy máy nào phù hợp tiêu chí bộ lọc. Đang đợi...")
                time.sleep(60)
                continue

            # ĐÃ SỬA: Thêm "sleep infinity" để giữ container luôn chạy, không bị tự hủy sau khi kết thúc lệnh khởi động
            onstart_cmd = (
                "export DEBIAN_FRONTEND=noninteractive && "
                "apt-get update && apt-get install -y git python3-pip python3-venv && "
                "git clone https://github.com /app && "
                "cd /app && python3 -m venv venv && "
                "./venv/bin/pip install --upgrade pip && "
                "./venv/bin/pip install -r requirements.txt --no-cache-dir && "
                "export TOKEN='rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3' && "
                "nohup ./venv/bin/python3 main.py > agent.log 2>&1 & "
                "echo 'GRADIENTS AGENT STARTED' && "
                "sleep infinity"
            )

            rent_payload = {
                "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args",
                "onstart": onstart_cmd
            }

            # GIỮ NGUYÊN: Phương thức PUT gửi tới endpoint asks chuẩn của Vast.ai
            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=40)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}! Đợi 3 phút để hệ thống kiểm tra trạng thái khởi động...")
                time.sleep(180)  
            else:
                print(f"[X] Thuê thất bại. Mã lỗi: {rent_resp.status_code} - Phản hồi: {rent_resp.text}")
                time.sleep(40)
        else:
            print(f"[X] Lỗi kết nối cổng tìm kiếm máy (Status: {resp.status_code})")
            time.sleep(60)
    except Exception as e:
        print(f"[ERROR] Phát sinh ngoại lệ: {e}")
        time.sleep(60)

    time.sleep(20)
