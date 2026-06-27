import os
import requests
import time
import json

# ====================== CẤU HÌNH GỐC NGUYÊN BẢN CỦA BẠN ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
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

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
        return []
    except:
        return []

def create_onstart_script():
    return f"""#!/bin/bash
echo "=== Agent OnStart Started - $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
git config --global credential.helper ''
git config --global --add safe.directory /app
rm -rf /app
if git clone --depth 1 {GITHUB_DOWNLOAD_URL} /app; then
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
            print(f" 🗑️ Xóa máy lỗi: {gpu_name} (ID: {inst_id})")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)
        elif status in ACTIVE_STATUS:
            valid_kept += 1
            if valid_kept > MAX_INSTANCES:
                print(f" 🗑️ Xóa máy thừa: {gpu_name} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)
                
    if valid_kept >= MAX_INSTANCES:
        print(f"[✅] Đã có {valid_kept} máy ổn định → Nghỉ 8 phút")
        time.sleep(480)
        continue

    print("[🔍] Đang tìm máy RTX 3090 series...")
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
                print("[⚠️] Không tìm thấy offer phù hợp. Thử lại sau 40 giây...")
                time.sleep(40)
                continue
                
            offers.sort(key=lambda x: x.get("dph_total", 999))
            best = offers.pop(0)
            offer_id = best["id"]
            gpu = best.get("gpu_name", "Unknown")
            print(f"[🎯] Tìm thấy {gpu} với giá {best.get('dph_total')}$ → Đang đặt thuê...")
            
            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": create_onstart_script()
            }
            
            rent_resp = requests.put(f"{BASE_URL}/instances/{offer_id}/", headers={"Authorization": f"Bearer {VAST_API_KEY}", "Content-Type": "application/json"}, json=rent_payload, timeout=90)
            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG MÁY {gpu}!")
                time.sleep(900)
            else:
                print(f"[❌] Thuê thất bại: {rent_resp.status_code}")
                time.sleep(30)
        else:
            print(f"[❌] Máy chủ /bundles/ phản hồi lỗi: {r.status_code}")
            time.sleep(40)
    except Exception as e:
        print(f"[ERROR] Lỗi hệ thống: {e}")
        time.sleep(40)
