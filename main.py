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


# ====================== CẤU HÌNH GỐC NGUYÊN BẢN CỦA BẠN ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "7057e1ebceac5d0dba64dcbc5a62d5b8f625fa18975ccec749f58cf5d76a17a2").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()
MAX_PRICE = 0.25
MAX_INSTANCES = 1

GITHUB_HOST = "https://github.com"
GITHUB_PATH = "/0hieutrung0-eng/Robot-vastai/tree/main"
GITHUB_REPO = GITHUB_HOST + GITHUB_PATH

GITHUB_DOWNLOAD_HOST = "https://github.com"
GITHUB_DOWNLOAD_PATH = "/0hieutrung0-eng/Robot-vastai.git"
GITHUB_DOWNLOAD_URL = GITHUB_DOWNLOAD_HOST + GITHUB_DOWNLOAD_PATH

# === ĐÃ SỬA: Chuyển chính xác sang cấu trúc API v0 theo chuẩn tài liệu Vast.ai ===
VAST_HOST = "https://console.vast.ai"
VAST_PATH = "/api/v1"
BASE_URL = VAST_HOST + VAST_PATH

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Accept": "application/json"
}

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

print_and_log("[START] Robot Vast.ai - Khởi động giữ duy nhất 1 GPU chạy ngầm vĩnh viễn")
print_and_log(f"[INFO] Kho mã nguồn mục tiêu: {GITHUB_REPO}")

if not VAST_API_KEY:
    print_and_log("[CRITICAL] CANH BAO: VAST_API_KEY dang bi trong!")


# ==============================================================================
# PHẦN 2: CÁC HÀM XỬ LÝ KẾT NỐI API VAST.AI (BẮT BUỘC THÊM DẤU / Ở CUỐI)
# ==============================================================================
def get_instances():
    try:
        print_and_log("[📡] Đang gửi yêu cầu lấy danh sách máy từ Vast.ai...")
        # API của Vast.ai bắt buộc phải có dấu gạch chéo / ở cuối đường dẫn instances/
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        
        print_and_log(f"[📡] Kết nối thành công! Mã phản hồi từ Vast.ai: HTTP {r.status_code}")
        
        if r.status_code != 200:
            print_and_log(f"[❌] Vast.ai từ chối kết nối (HTTP {r.status_code}): {r.text[:200]}")
            return []
            
        try:
            instances_list = r.json().get("instances", [])
            print_and_log(f"[📊] Đã nhận dữ liệu JSON. Tìm thấy tổng cộng: {len(instances_list)} máy trên tài khoản.")
            return instances_list
        except ValueError:
            print_and_log(f"[❌] API trả về Text/HTML chứ không phải JSON hợp lệ. Nội dung: {r.text[:200]}")
            return []
            
    except Exception as e:
        print_and_log(f"[ERROR] Không thể kết nối đến đối tượng Vast.ai: {e}")
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
    echo "→ Clone thanh cong" >> /root/agent.log
else
    echo "→ Clone that bai (Kiem tra token quyen truy cap)" >> /root/agent.log
fi
cd /app
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --no-cache-dir -q
fi
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
sleep infinity"""


# ==============================================================================
# PHẦN 3: VÒNG LẶP KIỂM TRA QUẢN LÝ VÀ TIẾN HÀNH THUÊ MÁY GPU CHẠY NGẦM
# ==============================================================================
while True:
    instances = get_instances()
    ACTIVE_STATUS = {"running", "loading", "creating", "starting"}
    running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() in ACTIVE_STATUS)
    print_and_log(f"[CHECK] Đang hoạt động: {running_count} | Tổng số máy: {len(instances)}")
    
    valid_kept = 0
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        gpu_name = inst.get("gpu_name", "Unknown")
        
        if status in ["error", "dead", "stopped", "failed"]:
            print_and_log(f" 🗑️ Phát hiện máy lỗi -> Tiến hành xóa: {gpu_name} (ID: {inst_id})")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)
        elif status in ACTIVE_STATUS:
            valid_kept += 1
            if valid_kept > MAX_INSTANCES:
                print_and_log(f" 🗑️ Phát hiện máy dư thừa -> Tiến hành xóa máy thừa: {gpu_name} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)
                
    if valid_kept >= MAX_INSTANCES:
        print_and_log(f"[✅] Đã có {valid_kept} máy hoạt động ổn định (Đạt tối đa) -> Nghỉ giữ luồng 8 phút...")
        for minute in range(8, 0, -1):
            print_and_log(f"[💤] Đang trong thời gian nghỉ. Sẽ quét lại sau {minute} phút...")
            time.sleep(60)
        continue

    print_and_log(f"[🔍] Số máy hoạt động ({valid_kept}) thấp hơn chỉ tiêu ({MAX_INSTANCES}). Tiến hành quét thị trường tìm RTX 3090...")
    query_filter = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"contains": "3090"}
    }
    
    try:
        print_and_log("[📡] Đang gửi bộ lọc tìm kiếm máy giá rẻ lên thị trường Vast.ai...")
        # API tìm máy của Vast.ai bắt buộc phải gọi vào đường dẫn bundles/
        r = requests.get(f"{BASE_URL}/bundles/", headers=HEADERS, params={"q": json.dumps(query_filter)}, timeout=20)
        
        if r.status_code == 200:
            try:
                res_data = r.json()
            except ValueError:
                print_and_log(f"[❌] Dữ liệu thị trường lấy về bị lỗi cấu trúc JSON. Nội dung: {r.text[:200]}")
                time.sleep(40)
                continue
                
            offers = res_data.get("offers", res_data.get("results", []))
            print_and_log(f"[📊] Kết quả tìm kiếm: Tìm thấy {len(offers)} máy thỏa mãn tiêu chuẩn (RTX 3090 & Giá <= {MAX_PRICE}$)")
            
            if not offers:
                print_and_log(f"[⚠️] Không có máy RTX 3090 nào giá rẻ hơn {MAX_PRICE}$ xuất hiện. Chờ 40 giây để quét lại...")
                time.sleep(40)
                continue
                
            offers.sort(key=lambda x: x.get("dph_total", 999))
            best = offers.pop(0)
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
            
            rent_resp = requests.put(f"{BASE_URL}/instances/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=90)
            if rent_resp.status_code in (200, 201):
                print_and_log(f"[🎉] XÁC NHẬN: THUÊ THÀNH CÔNG MÁY {gpu}! Hệ thống sẽ tạm nghỉ 15 phút để máy khởi động...")
                time.sleep(900)
            else:
                print_and_log(f"[❌] Lệnh thuê bị Vast.ai từ chối (HTTP {rent_resp.status_code}): {rent_resp.text}")
                time.sleep(30)
        else:
            print_and_log(f"[❌] Lấy dữ liệu thị trường thất bại (HTTP {r.status_code}): {r.text[:200]}")
            time.sleep(40)
    except Exception as e:
        print_and_log(f"[ERROR] Hệ thống phát sinh lỗi ngoại lệ trong quá trình quét: {e}")
        time.sleep(40)
