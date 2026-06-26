import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.23
MAX_INSTANCES = 1   # Đổi thành 2 nếu muốn chạy nhiều máy

BASE_URL = "https://vast.ai"
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
    
    # 1. XỬ LÝ MÁY LỖI (Bao gồm lỗi Driver, OCI, Daemon, Pull image)
    healthy_count = 0
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        actual_status = str(inst.get("actual_status", "")).lower()
        gpu = inst.get("gpu_name", "Unknown")
        
        error_keywords = ["error", "failed", "storage", "oci", "daemon", "pull", "unsatisfied"]
        if any(kw in status or kw in actual_status for kw in error_keywords):
            print(f"[🗑️] Phát hiện máy lỗi/không tương thích Driver {gpu} (ID: {inst_id}) → Destroy...")
            try:
                del_resp = requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                if del_resp.status_code == 200:
                    print(f"[OK] Destroy máy lỗi thành công")
                else:
                    print(f"[X] Gửi lệnh destroy lỗi, code: {del_resp.status_code}")
            except Exception as e:
                print(f"[X] Lỗi gửi lệnh xóa: {e}")
            time.sleep(10)
        else:
            # Chỉ đếm những máy thực sự khỏe mạnh
            healthy_count += 1

    print(f"[CHECK] Số máy khỏe mạnh hiện tại: {healthy_count}/{MAX_INSTANCES}")

    if healthy_count >= MAX_INSTANCES:
        print(f"[✅] ĐÃ ĐỦ MÁY SẠCH → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # 2. TÌM VÀ THUÊ MÁY MỚI (Áp dụng bộ lọc chống máy cũ)
    print("[🔍] Chưa đủ máy khỏe mạnh, đang tìm offer đạt chuẩn...")

    search_payload = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"in": ["RTX 3090 Ti", "RTX 3090"]},
        # GIẢI PHÁP 1: Ép buộc API chỉ lấy máy có Driver >= 550.00 để không bao giờ bị lỗi CUDA
        "driver_version": {"gte": "550.00"}, 
        "order": [["dph_total", "asc"]],
        "limit": 5
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

        if resp.status_code == 200 and resp.json().get("offers"):
            # Lấy object offer hợp lệ
            best = resp.json()["offers"]
            offer_id = best["id"]
            gpu = best.get("gpu_name")
            driver = best.get("driver_version", "Unknown")

            print(f"[🎯] Tìm thấy {gpu} (Driver: {driver}) → Tiến hành đặt thuê...")

            # GIẢI PHÁP 2: Dùng bản Image tương thích cao 12.1.1 kết hợp nohup (không treo tail -f)
            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                "disk": 40.0,
                "runtype": "args",
                "onstart": "apt-get update && apt-get install -y git python3-pip && git clone https://github.com /app && cd /app && pip install -r requirements.txt --no-cache-dir && nohup python3 main.py > agent.log 2>&1 & echo 'GRADIENTS AGENT STARTED'"
            }

            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=40)

            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG {gpu}! Đợi 3 phút để hệ thống thiết lập...")
                time.sleep(180)  # Quay lại vòng lặp sớm để phát hiện ngay nếu máy có lỗi phát sinh
            else:
                print(f"[X] Thuê thất bại. Phản hồi từ Vast: {rent_resp.status_code}")
                time.sleep(40)
        else:
            print("[X] Không tìm thấy máy đạt yêu cầu giá và phiên bản Driver")
            time.sleep(60)
    except Exception as e:
        print(f"[ERROR] Lỗi trong quá trình quét/thuê: {e}")
        time.sleep(60)

    time.sleep(20)
