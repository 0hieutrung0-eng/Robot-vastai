import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.25    # Đảm bảo bao phủ mức giá $0.229 - $0.269 thực tế trên sàn
MAX_INSTANCES = 1   

# SỬA LỖI GỐC: Tách biệt chính xác hai hệ thống Endpoint của Vast.ai
SYSTEM_URL = "https://console.vast.ai/api/v1"  # Dành cho quản lý máy và đặt thuê
SEARCH_URL = "https://vllm.vast.ai/api/v1"     # BẮT BUỘC dành riêng cho lọc tìm máy (/bundles)

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print(f"[START] Robot săn máy Vast.ai chuẩn hóa - Max {MAX_INSTANCES} máy")

def get_instances():
    try:
        # Lấy danh sách máy chạy qua SYSTEM_URL
        r = requests.get(f"{SYSTEM_URL}/instances/", headers=HEADERS, timeout=12)
        if r.status_code == 200:
            return r.json().get("instances", []), True
        else:
            print(f"[API Error] get_instances Status: {r.status_code}")
    except Exception as e:
        print(f"[API Exception] get_instances: {e}")
    return [], False

while True:
    try:
        instances, is_api_ok = get_instances()
        
        if not is_api_ok:
            print("[⚠️] Lỗi kết nối API Vast.ai. Thử lại sau 10 giây...")
            time.sleep(10)
            continue
        
        # 1. KIỂM TRA VÀ DỌN DẸP MÁY LỖI KẸT
        healthy_count = 0
        for inst in instances:
            inst_id = inst.get("id")
            status = str(inst.get("status", "")).lower()
            actual_status = str(inst.get("actual_status", "")).lower()
            status_msg = str(inst.get("status_msg", "")).lower()
            gpu = inst.get("gpu_name", "Unknown")
            
            error_keywords = ["error", "failed", "storage", "oci", "daemon", "pull", "runc", "template not found"]
            if any(kw in status or kw in actual_status or kw in status_msg for kw in error_keywords):
                print(f"[🗑️] Máy lỗi kẹt {gpu} (ID: {inst_id}) → Destroy gấp...")
                try:
                    requests.delete(f"{SYSTEM_URL}/instances/{inst_id}/", headers=HEADERS, timeout=10)
                    print(f"[OK] Đã dọn dẹp xong máy lỗi {inst_id}")
                except Exception as e:
                    print(f"[X] Lỗi xóa máy: {e}")
                time.sleep(5)
            else:
                healthy_count += 1

        if healthy_count >= MAX_INSTANCES:
            print(f"[✅] ĐÃ ĐỦ MÁY KHỎE MẠNH ({healthy_count}/{MAX_INSTANCES}) → Nghỉ 8 phút...")
            time.sleep(480)
            continue

        # 2. QUÉT LIÊN TỤC KHÔNG NGỪNG NẾU THIẾU MÁY
        print(f"[🔍] Chưa đủ máy ({healthy_count}/{MAX_INSTANCES}) → Đang tìm kiếm trên sàn...")

        search_payload = {
            "q": {
                "rentable": {"eq": True},
                "rented": {"eq": False},
                "dph_total": {"lte": MAX_PRICE},
                "gpu_name": {"in": ["RTX 3090 Ti", "RTX 3090", "RTX 4070 Ti", "RTX 3080 Ti"]},
                "driver_version": {"gte": 535.00}
            },
            "order": [["dph_total", "asc"]],
            "limit": 3
        }

        # Gọi API tìm kiếm thông qua SEARCH_URL (vllm.vast.ai)
        resp = requests.post(f"{SEARCH_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=12)

        if resp.status_code == 200:
            res_json = resp.json()
            offers = res_json.get("offers", []) if isinstance(res_json, dict) else res_json
            
            if isinstance(offers, list) and len(offers) > 0:
                # Trích xuất chuẩn xác thông tin phần tử đầu tiên ngon nhất trong mảng
                best = offers[0]
                offer_id = best["id"]
                gpu = best.get("gpu_name")
                price = best.get("dph_total")

                print(f"[🎯] KHỚP MÁY: {gpu} ({price}$/h) (ID: {offer_id}) → Tiến hành đặt thuê...")

                # ĐÃ SỬA: Sửa lại đúng đường dẫn git clone đồng thời bọc chuỗi lệnh vào trong bash -c
                onstart_cmd = (
                    "bash -c '"
                    "export DEBIAN_FRONTEND=noninteractive && "
                    "apt-get update && apt-get install -y git python3-pip python3-venv && "
                    "git clone https://github.com /app && "
                    "cd /app && python3 -m venv venv && "
                    "./venv/bin/pip install --upgrade pip && "
                    "./venv/bin/pip install -r requirements.txt --no-cache-dir && "
                    "export TOKEN=\"rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3\" && "
                    "nohup ./venv/bin/python3 main.py > agent.log 2>&1 & "
                    "echo \"GRADIENTS AGENT STARTED SUCCESSFULLY\" && "
                    "sleep infinity'"
                )

                # ĐÃ SỬA CHÍ MẠNG: Đổi runtype từ "args" thành "bash" để Vast.ai dịch được chuỗi lệnh của bạn
                rent_payload = {
                    "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                    "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                    "disk": 40.0,
                    "runtype": "bash",
                    "onstart": onstart_cmd
                }

                # Gửi lệnh đặt thuê thông qua SYSTEM_URL (console.vast.ai)
                rent_resp = requests.put(f"{SYSTEM_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=30)

                if rent_resp.status_code in (200, 201):
                    print(f"[🎉] THUÊ THÀNH CÔNG MÁY {gpu}! Chờ 3 phút hệ thống nạp...")
                    time.sleep(180)   
                else:
                    print(f"[X] Host từ chối cắn lệnh (Mã: {rent_resp.status_code}). Tiếp tục quét lại...")
                    time.sleep(3)
            else:
                print("[⏳] Không có máy trống thỏa mãn bộ lọc. Quét lại ngay lập tức...")
                time.sleep(1)
        else:
            print(f"[X] Lỗi API Tìm kiếm ({resp.status_code}) - Vui lòng kiểm tra lại VAST_API_KEY")
            time.sleep(5)

    except Exception as e:
        print(f"[⚙️ Lỗi Vòng Lặp] {e}")
        time.sleep(3)

    time.sleep(1)
