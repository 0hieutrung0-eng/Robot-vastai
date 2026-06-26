import os
import requests
import time

# GIỮ NGUYÊN KHÔNG THAY ĐỔI ENDPOINT GỐC
BASE_URL = "https://console.vast.ai/api/v0"

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.23
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
            "gpu_name": {"in": ["RTX 3090 Ti", "RTX 3090"]},
            # BẮT BUỘC: Đảm bảo Driver máy chủ >= 550.00 để không bị sập lỗi OCI với CUDA 12.4.1
            "driver_version": {"gte": 550.00}
        },
        "order": [["dph_total", "asc"]],
        "limit": 5
    }

    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=15)

        if resp.status_code == 200 and resp.json().get("offers"):
            offers = resp.json()["offers"]
            
            # ĐÃ SỬA: Kiểm tra kiểu dữ liệu và trích xuất phần tử đầu tiên an toàn tuyệt đối
            if isinstance(offers, list) and len(offers) > 0:
                best = offers[0]
            else:
                best = offers

            offer_id = best["id"]
            gpu = best.get("gpu_name")

            print(f"[🎯] Tìm thấy {gpu} → Thuê...")

            # SỬA LỖI LINUX: Cô lập môi trường bằng venv và sửa chính xác URL Git Clone cho Gradients Agent
            onstart_cmd = (
                "export DEBIAN_FRONTEND=noninteractive && "
                "apt-get update && apt-get install -y git python3-pip python3-venv && "
                "git clone https://github.com/gradients-io/scraper-agent.git /app && "
                "cd /app && python3 -m venv venv && "
                "./venv/bin/pip install --upgrade pip && "
                "./venv/bin/pip install -r requirements.txt --no-cache-dir && "
                "export TOKEN='rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3' && "
                "nohup ./venv/bin/python3 main.py > agent.log 2>&1 & "
                "echo 'GRADIENTS AGENT STARTED'"
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
                time.sleep(180)  # Tối ưu thời gian ngủ ngắn lại để bot nhanh chóng quay lại quản lý máy
            else:
                print(f"[X] Thuê thất bại: {rent_resp.status_code}")
                time.sleep(40)
        else:
            print("[X] Chưa tìm thấy máy")
            time.sleep(60)
    except Exception as e:
        print(f"[ERROR] {e}")
        time.sleep(60)

    time.sleep(20)
