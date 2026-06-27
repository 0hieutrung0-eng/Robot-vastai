import os
import requests
import time
import json
import threading
from fastapi import FastAPI
import uvicorn

# ==============================================================================
# PHẦN 1: KHỞI TẠO MÁY CHỦ WEB BẮT BUỘC ĐỂ GIỮ HUGGING FACE SPACES LUÔN "RUNNING"
# ==============================================================================
app = FastAPI()
SYSTEM_STATUS = "Robot vừa khởi động, đang chuẩn bị quét..."

@app.get("/")
def read_root():
    return {
        "status": "active",
        "robot_log": SYSTEM_STATUS,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def run_web_server():
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

threading.Thread(target=run_web_server, daemon=True).start()


# ====================== CẤU HÌNH HỆ THỐNG VÀ KEY XÁC THỰC ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1

GITHUB_DOWNLOAD_PATH = "/0hieutrung0-eng/Robot-vastai.git"
BASE_URL = "https://console.vast.ai/api/v1"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

print_and_log("[START] Robot Vast.ai v1 - Tự Động Định Tuyến Tối Hậu (Fallback Engine)")

if not VAST_API_KEY or not AGENT_TOKEN:
    print_and_log("[❌] LỖI CẤU HÌNH: Thiếu VAST_API_KEY hoặc AGENT_TOKEN!")
    while True:
        time.sleep(3600)


# ==============================================================================
# PHẦN 2: CÁC HÀM XỬ LÝ KẾT NỐI API VAST.AI CHUẨN XÁC
# ==============================================================================
def get_instances():
    try:
        print_and_log("[📡] Đang kiểm tra danh sách máy ĐÃ THUÊ trên tài khoản...")
        url = f"{BASE_URL}/instances/?owner=me&api_key={VAST_API_KEY}"
        r = requests.get(url, headers=HEADERS, timeout=20)

        if r.status_code == 200:
            data = r.json()
            instances_list = data.get("instances", []) if isinstance(data, dict) else data
            if not isinstance(instances_list, list):
                instances_list = []
            print_and_log(f"[📊] Số máy đang có trong tài khoản: {len(instances_list)} máy.")
            return instances_list
        else:
            return []
    except Exception as e:
        print_and_log(f"[ERROR] Ngoại lệ hàm get_instances: {e}")
        return []

def create_onstart_script():
    AUTHENTICATED_URL = f"https://{AGENT_TOKEN}@github.com{GITHUB_DOWNLOAD_PATH}"
    return f"""#!/bin/bash
echo "=== Agent OnStart Started - $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
git config --global credential.helper ''
git config --global --add safe.directory /app
rm -rf /app
if git clone --depth 1 {AUTHENTICATED_URL} /app; then
    echo "→ Clone thành công" >> /root/agent.log
else
    echo "→ Clone thất bại" >> /root/agent.log
fi
cd /app
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --no-cache-dir -q
fi
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
sleep infinity"""


# ==============================================================================
# PHẦN 3: VÒNG LẶP SĂN MÁY ĐA PHƯƠNG THỨC VÀ ĐA ENDPOINT
# ==============================================================================
# Chuỗi lọc JSON phẳng mã hóa chuẩn để test
encoded_q = "%7B%22verified%22%3Atrue%2C%22external%22%3Afalse%2C%22rentable%22%3Atrue%2C%22rented%22%3Afalse%7D"

while True:
    instances = get_instances()
    ACTIVE_STATUS = {"running", "loading", "creating", "starting"}
    
    running_count = 0
    if instances:
        running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() in ACTIVE_STATUS)
    print_and_log(f"[CHECK] Đang hoạt động: {running_count} | Tổng số máy: {len(instances or [])}")
    
    valid_kept = 0
    if instances:
        for inst in instances:
            inst_id = inst.get("id")
            status = str(inst.get("status", "")).lower()
            gpu_name = inst.get("gpu_name", "Unknown")
            
            if status in ["error", "dead", "stopped", "failed"]:
                print_and_log(f" 🗑️ Phát hiện máy lỗi -> Xóa máy lỗi: {gpu_name} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, params={"api_key": VAST_API_KEY}, timeout=15)
                time.sleep(8)
            elif status in ACTIVE_STATUS:
                valid_kept += 1
                if valid_kept > MAX_INSTANCES:
                    print_and_log(f" 🗑️ Vượt chỉ tiêu -> Xóa bớt máy dư thừa: {gpu_name} (ID: {inst_id})")
                    requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, params={"api_key": VAST_API_KEY}, timeout=15)
                    time.sleep(8)
                
    if valid_kept >= MAX_INSTANCES:
        print_and_log(f"[✅] Đã có {valid_kept} máy chạy ổn định -> Tạm nghỉ quét 8 phút...")
        for minute in range(8, 0, -1):
            time.sleep(60)
        continue

    print_and_log(f"[🔍] Bắt đầu chu kỳ quét thị trường thông minh...")
    
    # DANH SÁCH CÁC ĐƯỜNG ĐI CHIẾN LƯỢC SẼ ĐƯỢC THỬ NGHIỆM LIÊN TỤC
    strategies = [
        {"name": "GET /bundles (Dạng mới không dấu gạch chéo)", "method": "GET", "url": f"{BASE_URL}/bundles?q={encoded_q}&api_key={VAST_API_KEY}"},
        {"name": "GET /bundles/ (Dạng có dấu gạch chéo)", "method": "GET", "url": f"{BASE_URL}/bundles/?q={encoded_q}&api_key={VAST_API_KEY}"},
        {"name": "GET /asks (Cổng phân phối thô)", "method": "GET", "url": f"{BASE_URL}/asks?q={encoded_q}&api_key={VAST_API_KEY}"},
        {"name": "GET /machines (Cổng phụ)", "method": "GET", "url": f"{BASE_URL}/machines?api_key={VAST_API_KEY}"}
    ]
    
    offers = []
    success_strategy_name = None
    
    for strg in strategies:
        try:
            print_and_log(f" 📡 Đang thử nghiệm chiến lược: {strg['name']}...")
            if strg["method"] == "GET":
                r = requests.get(strg["url"], headers=HEADERS, timeout=15)
            
            if r.status_code == 200:
                res_data = r.json()
                # Bóc tách mảng từ mọi cấu trúc key có thể có
                if isinstance(res_data, dict):
                    offers = res_data.get("offers", res_data.get("asks", res_data.get("machines", res_data.get("results", res_data.get("instances", [])))))
                elif isinstance(res_data, list):
                    offers = res_data
                    
                if offers and isinstance(offers, list):
                    success_strategy_name = strg["name"]
                    print_and_log(f" [🎯 SUCCESS] Kết nối thành công bằng chiến lược: {success_strategy_name}!")
                    break
            else:
                print(f"   -> Thất bại (Mã phản hồi: {r.status_code})", flush=True)
        except Exception as e:
            print(f"   -> Lỗi kết nối ngoại lệ: {e}", flush=True)
            
    if not offers:
        print_and_log("[⚠️] Toàn bộ chiến lược kết nối API đều thất bại hoặc thị trường trống rỗng. Thử lại sau 30 giây...")
        time.sleep(30)
        continue
        
    # SÀNG LỌC VÀ LỌC GIÁ BẰNG PYTHON ENGINE TẠI CLIENT
    valid_offers = []
    for o in offers:
        if not isinstance(o, dict):
            continue
            
        o_id = o.get("id", o.get("machine_id"))
        if o_id is None:
            continue
            
        price = float(o.get("dph_total", o.get("price", 999)))
        gpu_name_str = str(o.get("gpu_name", ""))
        
        # Lọc chính xác máy RTX 3090 dựa vào chuỗi ký tự và giá tối đa
        if "3090" in gpu_name_str and price <= MAX_PRICE:
            valid_offers.append({
                "id": o_id,
                "gpu_name": gpu_name_str,
                "price": price
            })
            
    print_and_log(f"[📊] Kết quả xử lý: Tìm thấy {len(valid_offers)} máy RTX 3090 phù hợp với giá trần <= {MAX_PRICE}$")
    
    if not valid_offers:
        time.sleep(30)
        continue
        
    # Sắp xếp lấy máy có giá thành tối ưu nhất
    valid_offers.sort(key=lambda x: x["price"])
    best_machine = valid_offers[0]
    
    print_and_log(f"[🎯] CHỌN ĐƯỢC MÁY RẺ NHẤT: ID {best_machine['id']} - Tên: {best_machine['gpu_name']} - Giá {best_machine['price']}$/giờ. Tiến hành thuê...")
    
    rent_payload = {
        "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
        "disk": 40.0,
        "runtype": "ssh_direct",
        "onstart": create_onstart_script()
    }
    
    # Thực hiện lệnh thuê máy POST trực tiếp
    try:
        rent_resp = requests.post(
            f"{BASE_URL}/asks/{best_machine['id']}/",
            headers=HEADERS,
            params={"api_key": VAST_API_KEY},
            json=rent_payload,
            timeout=60
        )
        
        if rent_resp.status_code in (200, 201):
            print_and_log(f"[🎉] THUÊ MÁY THÀNH CÔNG! Chờ máy thiết lập cài đặt...")
            time.sleep(900)
        else:
            print_and_log(f"[❌] Lỗi khi gửi lệnh thuê máy (Mã: {rent_resp.status_code}): {rent_resp.text}")
            time.sleep(20)
    except Exception as e:
        print_and_log(f"[ERROR] Ngoại lệ luồng thuê máy: {e}")
        time.sleep(20)
