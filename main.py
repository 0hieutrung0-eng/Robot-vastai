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
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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

print_and_log("[START] Robot Vast.ai v1 - Bản Khớp Trực Diện /instances/ POST")

if not VAST_API_KEY or not AGENT_TOKEN:
    print_and_log("[❌] LỖI CẤU HÌNH: Thiếu VAST_API_KEY hoặc AGENT_TOKEN!")
    while True:
        time.sleep(3600)


# ==============================================================================
# PHẦN 2: HÀM KIỂM TRA MÁY ĐÃ THUÊ CỦA BẠN (DÙNG PARAMS RIÊNG)
# ==============================================================================
def get_my_rented_instances():
    try:
        # Lấy danh sách máy BẠN ĐÃ THUÊ bằng cách truyền owner=me trên URL GET
        url = f"{BASE_URL}/instances/?owner=me&api_key={VAST_API_KEY}"
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            data = r.json()
            instances_list = data.get("instances", []) if isinstance(data, dict) else data
            if not isinstance(instances_list, list):
                instances_list = []
            return instances_list
        return []
    except Exception as e:
        print_and_log(f"[ERROR] Lỗi hàm get_my_rented_instances: {e}")
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
# PHẦN 3: VÒNG LẶP SĂN MÁY TẤN CÔNG QUA PHƯƠNG THỨC POST CHUẨN
# ==============================================================================
while True:
    my_instances = get_my_rented_instances()
    ACTIVE_STATUS = {"running", "loading", "creating", "starting"}
    
    running_count = 0
    if my_instances:
        running_count = sum(1 for inst in my_instances if str(inst.get("status", "")).lower() in ACTIVE_STATUS)
    print_and_log(f"[CHECK] Đang hoạt động: {running_count} | Tổng số máy đã thuê: {len(my_instances)}")
    
    valid_kept = 0
    if my_instances:
        for inst in my_instances:
            inst_id = inst.get("id")
            status = str(inst.get("status", "")).lower()
            gpu_name = inst.get("gpu_name", "Unknown")
            
            if status in ["error", "dead", "stopped", "failed"]:
                print_and_log(f" 🗑️ Xóa máy lỗi: {gpu_name} (ID: {inst_id})")
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

    print_and_log(f"[🔍] Gửi lệnh POST lấy danh sách thị trường từ /instances/...")
    
    # Cấu trúc payload lọc quy chuẩn của Vast.ai dựa theo cấu trúc chẩn đoán
    market_payload = {
        "verified": True,
        "external": False,
        "rentable": True,
        "rented": False
    }
    
    try:
        # Tấn công trực diện vào /instances/ bằng phương thức POST kèm payload bộ lọc
        r = requests.post(
            f"{BASE_URL}/instances/",
            headers=HEADERS,
            params={"api_key": VAST_API_KEY},
            json=market_payload,
            timeout=25
        )
        
        if r.status_code == 200:
            res_data = r.json()
            offers = res_data.get("instances", [])
            
            if not offers:
                print_and_log(f"[⚠️] Không tìm thấy máy nào từ sàn. Đợi quét lại sau 30 giây...")
                time.sleep(30)
                continue
                
            valid_offers = []
            for o in offers:
                if not isinstance(o, dict):
                    continue
                o_id = o.get("id")
                if o_id is None:
                    continue
                
                price = float(o.get("dph_total", o.get("price", 999)))
                gpu_name_str = str(o.get("gpu_name", ""))
                
                # Sàng lọc theo cấu hình yêu cầu tại Client-side (RTX 3090 và giá trần)
                if "3090" in gpu_name_str and price <= MAX_PRICE:
                    valid_offers.append({
                        "id": o_id,
                        "gpu_name": gpu_name_str,
                        "price": price
                    })
                
            print_and_log(f"[📊] Kết quả: Tìm thấy {len(valid_offers)} máy RTX 3090 phù hợp.")
            
            if not valid_offers:
                time.sleep(30)
                continue
                
            # Sắp xếp chọn máy rẻ nhất
            valid_offers.sort(key=lambda x: x["price"])
            best_machine = valid_offers[0]
            
            print_and_log(f"[🎯] CHỌN ĐƯỢC MÁY RẺ NHẤT: ID {best_machine['id']} - Giá {best_machine['price']}$/giờ. Tiến hành thuê...")
            
            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": create_onstart_script()
            }
            
            # Thực thi đặt thuê máy công khai
            rent_resp = requests.post(
                f"{BASE_URL}/asks/{best_machine['id']}/",
                headers=HEADERS,
                params={"api_key": VAST_API_KEY},
                json=rent_payload,
                timeout=60
            )
            
            if rent_resp.status_code in (200, 201):
                print_and_log(f"[🎉] THUÊ MÁY THÀNH CÔNG! Chờ máy khởi động...")
                time.sleep(900)
            else:
                log_api_error("LỆNH THUÊ MÁY (POST /asks/)", rent_resp)
                time.sleep(20)
        else:
            log_api_error("QUÉT THỊ TRƯỜNG (POST /instances/)", r)
            time.sleep(30)
            
    except Exception as e:
        print_and_log(f"[ERROR] Lỗi luồng hệ thống: {e}")
        time.sleep(30)
