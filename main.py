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

@app.get("/")
def read_root():
    return {
        "status": "active",
        "message": "Robot Vast.ai dang chay ngam on dinh",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def run_web_server():
    # Hugging Face yêu cầu ứng dụng phải lắng nghe chính xác tại cổng 7860
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

# Khởi chạy máy chủ web trong một luồng phụ tách biệt (Thread) để không chặn vòng lặp thuê máy
threading.Thread(target=run_web_server, daemon=True).start()


# ====================== CẤU HÌNH GỐC NGUYÊN BẢN CỦA BẠN ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "7057e1ebceac5d0dba64dcbc5a62d5b8f625fa18975ccec749f58cf5d76a17a2").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()
MAX_PRICE = 0.25
MAX_INSTANCES = 1

# ====================== TÁCH BIẾN ĐƯỜNG DẪN GITHUB XEM WEB ======================
GITHUB_HOST = "https://github.com"
GITHUB_PATH = "/0hieutrung0-eng/Robot-vastai/tree/main"
GITHUB_REPO = GITHUB_HOST + GITHUB_PATH

# ====================== TÁCH BIẾN ĐƯỜNG DẪN GITHUB TẢI FILE (.GIT) ======================
GITHUB_DOWNLOAD_HOST = "https://github.com"
GITHUB_DOWNLOAD_PATH = "/0hieutrung0-eng/Robot-vastai.git"
GITHUB_DOWNLOAD_URL = GITHUB_DOWNLOAD_HOST + GITHUB_DOWNLOAD_PATH

# ====================== TÁCH BIẾN BASE URL VAST.AI (ĐỒNG BỘ API V1) ======================
VAST_HOST = "https://vast.ai"
VAST_PATH = "/api/v1"
BASE_URL = VAST_HOST + VAST_PATH

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Accept": "application/json"
}

print("[START] Robot Vast.ai - Khởi động giữ duy nhất 1 GPU chạy ngầm vĩnh viễn")
print(f"[INFO] Kho mã nguồn mục tiêu: {GITHUB_REPO}")

if not VAST_API_KEY:
    print("[CRITICAL] CANH BAO: VAST_API_KEY dang bi trong! He thong co the bi lap loi.")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
        else:
            print(f"[❌] Loi ket noi API Vast.ai (HTTP {r.status_code}): {r.text}")
            return []
    except Exception as e:
        print(f"[ERROR] Khong the ket noi den Vast.ai: {e}")
        return []

def create_onstart_script():
    # Sử dụng AGENT_TOKEN chèn trực tiếp vào đường dẫn tải về để máy GPU có quyền clone kho private
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
    print(f"[CHECK] Running: {running_count} | Total: {len(instances)}")
    
    valid_kept = 0
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        gpu_name = inst.get("gpu_name", "Unknown")
        
        if status in ["error", "dead", "stopped", "failed"]:
            print(f" 🗑️ Xoa may gap loi: {gpu_name} (ID: {inst_id})")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)
        elif status in ACTIVE_STATUS:
            valid_kept += 1
            if valid_kept > MAX_INSTANCES:
                print(f" 🗑️ Xoa may du thua: {gpu_name} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)
                
    if valid_kept >= MAX_INSTANCES:
        print(f"[✅] Da co {valid_kept} may hoat dong on dinh -> Nghi giu luong 8 phut")
        time.sleep(480)
        continue

    print("[🔍] Chuyen sang quet tim may RTX 3090 series thich hop...")
    query_filter = {
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"contains": "3090"}
    }
    
    try:
        r = requests.get(f"{BASE_URL}/bundles", headers=HEADERS, params={"q": json.dumps(query_filter)}, timeout=20)
        if r.status_code == 200:
            res_data = r.json()
            offers = res_data.get("offers", res_data.get("results", []))
            
            if not offers:
                print(f"[⚠️] Khong tim thay may nao dat tieu chi gia duoi {MAX_PRICE}$. Quet lai sau 40 giay...")
                time.sleep(40)
                continue
                
            offers.sort(key=lambda x: x.get("dph_total", 999))
            best = offers.pop(0)
            offer_id = best["id"]
            gpu = best.get("gpu_name", "Unknown")
            print(f"[🎯] Phat hien {gpu} voi gia cuc tot {best.get('dph_total')}$ -> Dang gui lenh thue...")
            
            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": create_onstart_script()
            }
            
            rent_resp = requests.put(f"{BASE_URL}/instances/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=90)
            if rent_resp.status_code in (200, 201):
                print(f"[🎉] TIẾN TRÌNH THUÊ THÀNH CÔNG MÁY {gpu}!")
                time.sleep(900)
            else:
                print(f"[❌] Yeu cau thue that bai. Thong tin phan hoi (HTTP {rent_resp.status_code}): {rent_resp.text}")
                time.sleep(30)
        else:
            print(f"[❌] May chu lay thong tin bundles bao loi (HTTP {r.status_code}): {r.text}")
            time.sleep(40)
    except Exception as e:
        print(f"[ERROR] He thong phat sinh loi ngoai le: {e}")
        time.sleep(40)
