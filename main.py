import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
MAX_PRICE = 0.25    # Giữ mức giá thực tế để có máy tốt
MAX_INSTANCES = 1   


BASE_URL = "https://console.vast.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print(f"[START] Robot quét liên tục - Max {MAX_INSTANCES} máy")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=12)
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
            print("[⚠️] Lỗi kết nối API Vast.ai. Thử lại sau 15 giây...")
            time.sleep(15)
            continue
        
        # 1. KIỂM TRA VÀ DỌN DẸP MÁY LỖI
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
                    requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=10)
                    print(f"[OK] Đã dọn dẹp xong máy lỗi {inst_id}")
                except Exception as e:
                    print(f"[X] Lỗi xóa máy: {e}")
                time.sleep(5)
            else:
                healthy_count += 1

        # Nếu đã đủ số lượng máy khỏe mạnh, bot sẽ nghỉ 8 phút
        if healthy_count >= MAX_INSTANCES:
            print(f"[✅] ĐÃ ĐỦ MÁY KHỎE MẠNH ({healthy_count}/{MAX_INSTANCES}) → Nghỉ 8 phút...")
            time.sleep(480)
            continue

        # 2. QUÉT LIÊN TỤC NẾU CHƯA TÌM ĐƯỢC MÁY
        print(f"[🔍] Chưa đủ máy ({healthy_count}/{MAX_INSTANCES}) → Đang quét tìm máy trên sàn...")

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

        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=12)

        if resp.status_code == 200:
            res_json = resp.json()
            offers = res_json.get("offers", []) if isinstance(res_json, dict) else res_json
            
            if isinstance(offers, list) and len(offers) > 0:
                best = offers[0]
                offer_id = best["id"]
                gpu = best.get("gpu_name")
                price = best.get("dph_total")

                print(f"[🎯] KHỚP MÁY: {gpu} ({price}$/h) (ID: {offer_id}) → Gửi lệnh thuê...")

                onstart_cmd = (
                    "export DEBIAN_FRONTEND=noninteractive && "
                    "apt-get update && apt-get install -y git python3-pip python3-venv && "
                    "git clone https://github.com /app && "
                    "cd /app && python3 -m venv venv && "
                    "./venv/bin/pip install --upgrade pip && "
                    "./venv/bin/pip install -r requirements.txt --no-cache-dir && "
                    "export TOKEN='rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3' && "
                    "nohup ./venv/bin/python3 main.py > agent.log 2>&1 & "
                    "echo 'GRADIENTS AGENT STARTED SUCCESSFULLY' && "
                    "sleep infinity"
                )

                rent_payload = {
                    "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
                    "env": {"TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"},
                    "disk": 40.0,
                    "runtype": "args",
                    "onstart": onstart_cmd
                }

                rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=30)

                if rent_resp.status_code in (200, 201):
                    print(f"[🎉] THUÊ THÀNH CÔNG {gpu}! Đợi 3 phút để hệ thống cài đặt cấu hình...")
                    time.sleep(180)   
                else:
                    print(f"[X] Host từ chối lệnh thuê: {rent_resp.status_code}. Tiếp tục quét lại...")
                    time.sleep(3) # Chờ ngắn rồi quét tiếp máy khác
            else:
                # KHI KHÔNG TÌM THẤY MÁY: Giảm sleep xuống 1-2 giây để lặp lại chu kỳ quét ngay lập tức
                print("[⏳] Không có máy trống thỏa mãn bộ lọc. Đang lặp lại lệnh quét ngay...")
                time.sleep(1)
        else:
            print(f"[X] Lỗi API Tìm kiếm ({resp.status_code})")
            time.sleep(5)

    except Exception as e:
        print(f"[⚙️ Hệ thống] Gặp lỗi: {e}")
        time.sleep(5)

    # Khoảng đệm rất ngắn giữa các vòng lặp tránh gây nghẽn CPU của Render
    time.sleep(1)
