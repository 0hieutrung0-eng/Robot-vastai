import os
import requests
import time
import json

# ====================== CẤU HÌNH BIẾN MÔI TRƯỜNG AN TOÀN ======================
# Lấy API Key từ hệ thống, nếu trống sẽ báo lỗi ngay lập tức
VAST_API_KEY = os.getenv("VAST_API_KEY", "7057e1ebceac5d0dba64dcbc5a62d5b8f625fa18975ccec749f58cf5d76a17a2").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1

# ====================== ĐƯỜNG DẪN GITHUB XÁC THỰC BẢO MẬT ======================
# Sử dụng trực tiếp AGENT_TOKEN để GPU sau khi thuê có quyền Clone kho Private
GITHUB_DOWNLOAD_URL = f"https://{AGENT_TOKEN}@://github.com"

# ====================== CẤU HÌNH API VAST.AI ======================
BASE_URL = "https://vast.ai"
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Accept": "application/json"
}

print("[START] Robot Vast.ai - Khởi động giữ duy nhất 1 GPU chạy ngầm vĩnh viễn")

if not VAST_API_KEY:
    print("[CRITICAL] LỖI NGUYÊN NHÂN CHÍNH: VAST_API_KEY đang bị trống! Vui lòng cấu hình lại.")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
        else:
            print(f"[❌] Lỗi kết nối API Vast.ai (HTTP {r.status_code}): {r.text}")
            return []
    except Exception as e:
        print(f"[ERROR] Không thể kết nối Vast.ai: {e}")
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
    echo "→ Clone thất bại (Kiểm tra AGENT_TOKEN)" >> /root/agent.log
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
                print("[⚠️] Không tìm thấy offer RTX 3090 giá dưới 0.25$. Thử lại sau 40 giây...")
                time.sleep(40)
                continue
                
            offers.sort(key=lambda x: x.get("dph_total", 999))
            best = offers.pop(0)
            offer_id = best["id"]
            gpu = best.get("gpu_name", "Unknown")
            print(f"[🎯] Tìm thấy {gpu} với giá {best.get('dph_total')}$ → Đang tiến hành thuê...")
            
            rent_payload = {
                "image": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "disk": 40.0,
                "runtype": "ssh_direct",
                "onstart": create_onstart_script()
            }
            
            rent_resp = requests.put(f"{BASE_URL}/instances/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=90)
            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG MÁY {gpu}!")
                time.sleep(900)
            else:
                print(f"[❌] Thuê thất bại. Phản hồi hệ thống (HTTP {rent_resp.status_code}): {rent_resp.text}")
                time.sleep(30)
        else:
            print(f"[❌] Máy chủ Vast.ai phản hồi lỗi tìm máy (HTTP {r.status_code}): {r.text}")
            time.sleep(40)
    except Exception as e:
        print(f"[ERROR] Lỗi hệ thống phát sinh: {e}")
        time.sleep(40)
