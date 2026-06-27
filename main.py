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

def log_api_error(action_name, response):
    print_and_log(f"[❌ LỖI CHI TIẾT - {action_name}]")
    print(f"  -> URL đã gọi: {response.url}", flush=True)
    print(f"  -> HTTP Status Code: {response.status_code}", flush=True)
    print(f"  -> Nội dung phản hồi: {response.text}", flush=True)
    print("-" * 60, flush=True)

print_and_log("[START] Robot Vast.ai v1 - Fix Endpoint Bắt Máy Chợ Đen")

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
        # Lấy danh sách máy ĐÃ THUÊ của riêng mình
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
            log_api_error("LẤY DANH SÁCH MÁY ĐÃ THUÊ", r)
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
# PHẦN 3: VÒNG LẶP SĂN MÁY QUA ENDPOINT CHỢ CÔNG KHAI (/ASKS/)
# ==============================================================================
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

    print_and_log(f"[🔍] Đang quét thị trường tìm kiếm ưu đãi RTX 3090 công khai...")
    
    try:
        # THAY ĐỔI QUYẾT ĐỊNH: Gọi trực tiếp vào cổng /asks/ để lấy danh sách máy đang rao bán công khai
        # Kết hợp bộ lọc query string chuẩn hóa để ép server trả về đúng danh sách thị trường
        market_url = (
            f"{BASE_URL}/asks/?"
            "q=%7B%22verified%22%3A%7B%22eq%22%3Atrue%7D%2C%22external%22%3A%7B%22eq%22%3Afalse%7D%2C"
            "%22rentable%22%3A%7B%22eq%22%3Atrue%7D%2C%22rented%22%3A%7B%22eq%22%3Afalse%7D%7D"
            f"&api_key={VAST_API_KEY}"
        )
        
        r = requests.get(market_url, headers=HEADERS, timeout=30)
        
        if r.status_code == 200:
            res_data = r.json()
            
            # Trích xuất mảng danh sách máy chào thuê
            offers = []
            if isinstance(res_data, dict):
                offers = res_data.get("asks", res_data.get("offers", res_data.get("instances", res_data.get("results", []))))
            elif isinstance(res_data, list):
                offers = res_data
                
            if not offers:
                print_and_log("[⚠️] Hệ thống trả về danh sách trống. Thử lại sau 30 giây...")
                time.sleep(30)
                continue
                
            # Duyệt mảng và sàng lọc bằng Python Client để đảm bảo độ chính xác
            valid_offers = []
            for o in offers:
                if not isinstance(o, dict):
                    continue
                
                o_id = o.get("id", o.get("machine_id"))
                if o_id is None:
                    continue
                
                # Trích xuất giá tiền và tên GPU
                price = float(o.get("dph_total", o.get("price", 999)))
                gpu_name_str = str(o.get("gpu_name", ""))
                
                # Lọc thủ công: Phải chứa cụm từ 3090 và giá nhỏ hơn hoặc bằng giới hạn MAX_PRICE
                if "3090" in gpu_name_str and price <= MAX_PRICE:
                    valid_offers.append({
                        "id": o_id,
                        "gpu_name": gpu_name_str,
                        "price": price
                    })
            
            print_and_log(f"[📊] Kết quả: Tìm thấy {len(valid_offers)} máy RTX 3090 thỏa mãn giá <= {MAX_PRICE}$")
            
            if not valid_offers:
                time.sleep(30)
                continue
                
            # Sắp xếp để ưu tiên chọn máy có chi phí rẻ nhất
            valid_offers.sort(key=lambda x: x["price"])
            best_machine = valid_offers[0]
            
            print_and_log(f"[🎯] CHỌN ĐƯỢC MÁY RẺ NHẤT: ID {best_machine['id']} - Giá {best_machine['price']}$/giờ. Tiến hành thuê...")
            
            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": create_onstart_script()
            }
            
            # Thực hiện đặt lệnh thuê máy
            rent_resp = requests.post(
                f"{BASE_URL}/asks/{best_machine['id']}/",
                headers=HEADERS,
                params={"api_key": VAST_API_KEY},
                json=rent_payload,
                timeout=60
            )
            
            if rent_resp.status_code in (200, 201):
                print_and_log(f"[🎉] THUÊ MÁY THÀNH CÔNG! Chờ máy thiết lập cài đặt trong 15 phút...")
                time.sleep(900)
            else:
                log_api_error("LỆNH THUÊ MÁY (POST /asks/)", rent_resp)
                time.sleep(20)
        else:
            log_api_error("QUÉT THỊ TRƯỜNG (/asks/)", r)
            time.sleep(30)
            
    except Exception as e:
        print_and_log(f"[ERROR] Lỗi luồng hệ thống: {e}")
        time.sleep(30)
