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

GITHUB_HOST = "https://github.com"
GITHUB_PATH = "/0hieutrung0-eng/Robot-vastai/tree/main"
GITHUB_REPO = GITHUB_HOST + GITHUB_PATH

GITHUB_DOWNLOAD_HOST = "https://github.com"
GITHUB_DOWNLOAD_PATH = "/0hieutrung0-eng/Robot-vastai.git"

VAST_HOST = "https://console.vast.ai"
VAST_PATH = "/api/v1"
BASE_URL = VAST_HOST + VAST_PATH

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

# Hàm bổ trợ In lỗi chi tiết (Deep Debug)
def log_api_error(action_name, response):
    print_and_log(f"[❌ LỖI CHI TIẾT - {action_name}]")
    print(f"  -> URL: {response.url}", flush=True)
    print(f"  -> HTTP Status Code: {response.status_code}", flush=True)
    print(f"  -> Headers phản hồi: {dict(response.headers)}", flush=True)
    print(f"  -> Nội dung phản hồi (Raw Text): {response.text}", flush=True)
    try:
        print(f"  -> Cấu trúc JSON lỗi: {json.dumps(response.json(), indent=2)}", flush=True)
    except Exception:
        print("  -> Phản hồi không phải định dạng JSON hợp lệ.", flush=True)
    print("-" * 60, flush=True)

print_and_log("[START] Robot Vast.ai API v1 Diagnostic Mode - Khởi động")

if not VAST_API_KEY or not AGENT_TOKEN:
    print_and_log("[❌] LỖI CẤU HÌNH: Vui lòng điền VAST_API_KEY và AGENT_TOKEN vào Environment Variables!")
    while True:
        time.sleep(3600)


# ==============================================================================
# PHẦN 2: CÁC HÀM XỬ LÝ KẾT NỐI API VAST.AI (KÈM TRÌNH KIỂM TRA LỖI)
# ==============================================================================
def get_instances():
    try:
        print_and_log("[📡] Đang gửi yêu cầu lấy danh sách máy từ Vast.ai...")
        # Thử nghiệm với GET /instances truyền thống
        r = requests.get(
            f"{BASE_URL}/instances",
            headers=HEADERS,
            params={"owner": "me", "api_key": VAST_API_KEY},
            timeout=20
        )

        if r.status_code == 200:
            try:
                data = r.json()
                instances_list = data.get("instances", []) if isinstance(data, dict) else data
                if not isinstance(instances_list, list):
                    instances_list = []
                print_and_log(f"[📊] Tìm thấy tổng cộng: {len(instances_list)} máy trên tài khoản.")
                return instances_list
            except ValueError:
                print_and_log("[❌] API lấy danh sách trả về dữ liệu lỗi JSON.")
                return []
        else:
            log_api_error("LẤY DANH SÁCH MÁY (GET /instances)", r)
            return []
            
    except Exception as e:
        print_and_log(f"[ERROR] Ngoại lệ kết nối hàm get_instances: {e}")
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
# PHẦN 3: VÒNG LẶP KIỂM TRA QUẢN LÝ VÀ TIẾN HÀNH THUÊ MÁY GPU V1
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
                print_and_log(f" 🗑️ Phát hiện máy lỗi -> Tiến hành xóa: {gpu_name} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}", headers=HEADERS, params={"api_key": VAST_API_KEY}, timeout=15)
                time.sleep(8)
            elif status in ACTIVE_STATUS:
                valid_kept += 1
                if valid_kept > MAX_INSTANCES:
                    print_and_log(f" 🗑️ Phát hiện máy dư thừa -> Tiến hành xóa bớt máy thừa: {gpu_name} (ID: {inst_id})")
                    requests.delete(f"{BASE_URL}/instances/{inst_id}", headers=HEADERS, params={"api_key": VAST_API_KEY}, timeout=15)
                    time.sleep(8)
                
    if valid_kept >= MAX_INSTANCES:
        print_and_log(f"[✅] Đã có {valid_kept} máy hoạt động ổn định -> Nghỉ giữ luồng 8 phút...")
        for minute in range(8, 0, -1):
            print_and_log(f"[💤] Đang trong thời gian nghỉ. Sẽ quét lại sau {minute} phút...")
            time.sleep(60)
        continue

    print_and_log(f"[🔍] Số máy hoạt động ({valid_kept}) thấp hơn chỉ tiêu ({MAX_INSTANCES}). Tiến hành quét tìm RTX 3090...")
    
    # Chuẩn hóa cấu trúc bộ lọc linh hoạt để theo dõi phản ứng từ Server
    query_filter = {
        "verified": {"eq": True},
        "external": {"eq": False},
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "gpu_name": {"eq": "GeForce RTX 3090"},
        "dph_total": {"lte": MAX_PRICE}
    }
    
    try:
        print_and_log("[📡] Đang gửi bộ lọc tìm kiếm máy giá rẻ lên thị trường Vast.ai...")
        
        # Thử nghiệm Endpoint 1: POST /bundles (Cấu trúc cơ sở dữ liệu cũ)
        r = requests.post(
            f"{BASE_URL}/bundles", 
            headers=HEADERS, 
            params={"api_key": VAST_API_KEY},
            json={"q": query_filter}, 
            timeout=25
        )
        
        # Nếu Endpoint 1 báo lỗi 404 hoặc 405, hệ thống tự động fallback debug sang Endpoint 2: GET /bundles kèm chuỗi hóa JSON string
        if r.status_code in (404, 405):
            print_and_log("[🔄] Endpoint POST /bundles không khả dụng. Đang thử nghiệm Fallback sang GET /bundles với URL Query String...")
            query_json_string = json.dumps(query_filter)
            r = requests.get(
                f"{BASE_URL}/bundles",
                headers=HEADERS,
                params={"q": query_json_string, "api_key": VAST_API_KEY},
                timeout=25
            )

        # Nếu cả 2 đều thất bại, tiếp tục kiểm tra nốt endpoint phụ /instances/ làm cổng tìm kiếm công khai
        if r.status_code in (404, 405):
            print_and_log("[🔄] Vẫn gặp lỗi 404/405. Đang chuyển hướng sang cổng dò tìm cuối: POST /instances công khai...")
            r = requests.post(
                f"{BASE_URL}/instances",
                headers=HEADERS,
                params={"api_key": VAST_API_KEY},
                json={"q": query_filter},
                timeout=25
            )

        if r.status_code == 200:
            try:
                res_data = r.json()
            except ValueError:
                print_and_log(f"[❌] Dữ liệu thị trường lấy về bị lỗi JSON. Nội dung thô: {r.text[:200]}")
                time.sleep(40)
                continue
                
            offers = []
            if isinstance(res_data, dict):
                offers = res_data.get("instances", res_data.get("results", res_data.get("offers", [])))
            elif isinstance(res_data, list):
                offers = res_data
                
            print_and_log(f"[📊] Kết quả tìm kiếm thành công: Tìm thấy {len(offers)} máy thỏa mãn tiêu chuẩn")
            
            if not offers:
                print_and_log(f"[⚠️] Không có máy GeForce RTX 3090 nào giá rẻ hơn {MAX_PRICE}$. Quét lại sau 40 giây...")
                time.sleep(40)
                continue
                
            valid_offers = [o for o in offers if isinstance(o, dict) and o.get("id") is not None]
            if not valid_offers:
                time.sleep(40)
                continue
                
            valid_offers.sort(key=lambda x: float(x.get("dph_total", 999)))
            best = valid_offers[0]
            offer_id = best["id"]
            gpu = best.get("gpu_name", "Unknown")
            price = best.get("dph_total")
            print_and_log(f"[🎯] ĐÃ TÌM THẤY MÁY TỐT NHẤT: {gpu} giá {price}$/giờ! Đang gửi lệnh THUÊ NGAY...")
            
            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": create_onstart_script()
            }
            
            rent_resp = requests.post(
                f"{BASE_URL}/asks/{offer_id}", 
                headers=HEADERS, 
                params={"api_key": VAST_API_KEY},
                json=rent_payload, 
                timeout=90
            )
            
            if rent_resp.status_code in (200, 201):
                print_and_log(f"[🎉] XÁC NHẬN: THUÊ THÀNH CÔNG MÁY {gpu}! Tạm nghỉ 15 phút chờ máy setup...")
                time.sleep(900)
            else:
                log_api_error(f"LỆNH THUÊ MÁY (POST /asks/{offer_id})", rent_resp)
                time.sleep(30)
        else:
            log_api_error("TÌM KIẾM THỊ TRƯỜNG (MARKET SEARCH)", r)
            time.sleep(40)
            
    except Exception as e:
        print_and_log(f"[ERROR] Hệ thống phát sinh lỗi ngoại lệ vòng lặp chính: {e}")
        time.sleep(40)
