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

# ====================== TÁCH BIẾN BASE URL VAST.AI ======================
VAST_HOST = "https://console.vast.ai"
VAST_PATH = "/api/v0"
BASE_URL = VAST_HOST + VAST_PATH

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

print("[START] Robot Vast.ai - Khởi động giữ duy nhất 1 GPU")
print(f"[INFO] Kho mã nguồn mục tiêu: {GITHUB_REPO}")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
        else:
            print(f"[ERROR] API instances: {r.status_code} - {r.text}")
            return []
    except Exception as e:
        print(f"[ERROR] Lấy instances: {e}")
        return []

def create_onstart_script():
    # Sử dụng GITHUB_DOWNLOAD_URL bọc chuỗi ghép tách biến để máy ảo không lỗi lệnh tải code
    return f"""#!/bin/bash
echo "=== Agent OnStart Started - $(date) ===" > /root/agent.log
apt-get update && apt-get install -y git python3-pip curl
git config --global credential.helper ''
git config --global --add safe.directory /app
echo "[1/3] Cloning repository..." >> /root/agent.log
rm -rf /app
if git clone --depth 1 {GITHUB_DOWNLOAD_URL} /app; then
    echo "→ Clone thành công" >> /root/agent.log
else
    echo "→ Clone thất bại, tạo placeholder" >> /root/agent.log
    mkdir -p /app
    echo 'import time; print("Placeholder..."); time.sleep(999999)' > /app/main.py
fi
cd /app
if [ -f "requirements.txt" ]; then
    echo "[2/3] Installing dependencies..." >> /root/agent.log
    pip install -r requirements.txt --no-cache-dir -q || echo "Pip install warning" >> /root/agent.log
fi
echo "[3/3] Starting agent..." >> /root/agent.log
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
echo "✅ Agent started successfully - $(date)" >> /root/agent.log
sleep infinity"""

while True:
    instances = get_instances()
    ACTIVE_STATUS = {"running", "loading", "creating", "starting"}
    running_count = sum(1 for inst in instances if str(inst.get("status", "")).lower() in ACTIVE_STATUS)
    print(f"\n[CHECK] Running: {running_count} | Total: {len(instances)}")
    
    valid_kept = 0
    for inst in instances:
        inst_id = inst.get("id")
        status = str(inst.get("status", "")).lower()
        gpu_name = inst.get("gpu_name", "Unknown")
        
        # Dọn dẹp máy lỗi hệ thống
        if status in ["error", "dead", "stopped", "failed"]:
            print(f" 🗑️ Xóa máy lỗi: {gpu_name} (ID: {inst_id})")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)
        elif status in ACTIVE_STATUS:
            valid_kept += 1
            # Xóa các máy phụ thừa thãi nếu vượt định mức
            if valid_kept > MAX_INSTANCES:
                print(f" 🗑️ Xóa máy thừa: {gpu_name} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)
                
    if valid_kept >= MAX_INSTANCES:
        print(f"[✅] Đã có {valid_kept} máy ổn định → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # ====================== TIẾN HÀNH TÌM VÀ ĐẶT THUÊ ======================
    print("[🔍] Đang tìm máy RTX 3090 series...")
    
    # Cấu trúc phẳng POST nới lỏng bộ lọc càn quét diện rộng máy External/Unverified giá siêu rẻ
    search_payload = {
        "rentable": True,
        "rented": False,
        "dph_total_lte": MAX_PRICE,
        "gpu_name_contains": "3090",
        "order": [["dph_total", "asc"]],
        "limit": 5
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=search_payload, timeout=20)
        
        if resp.status_code == 200:
            res_data = resp.json()
            # Giải pháp fallback dự phòng cấu trúc tên mảng trả về của Vast.ai
            offers = res_data.get("offers", res_data.get("results", []))
            
            if not offers:
                print("[⚠️] Không tìm thấy offer phù hợp. Thử lại sau 40 giây...")
                time.sleep(40)
                continue
                
            # ĐÃ KHẮC PHỤC BIẾN HÀM HIỂN THỊ: Sử dụng .pop(0) lấy máy rẻ nhất đứng đầu danh sách
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
            
            # Đặt lệnh mua máy thông qua đúng API endpoint kích hoạt của Vast.ai v0
            rent_resp = requests.put(f"{BASE_URL}/asks/{offer_id}/", headers=HEADERS, json=rent_payload, timeout=90)
            
            if rent_resp.status_code in (200, 201):
                print(f"[🎉] THUÊ THÀNH CÔNG MÁY {gpu}!")
                time.sleep(900)  # Tạm nghỉ 15 phút chờ máy khởi tạo hệ điều hành
            else:
                print(f"[❌] Thuê thất bại. Mã trạng thái API: {rent_resp.status_code}")
                print(f"Chi tiết phản hồi lỗi: {rent_resp.text[:500]}")
                time.sleep(30)
        else:
            print(f"[❌] Máy chủ /bundles/ phản hồi lỗi: {resp.status_code}. Thử lại sau 40 giây...")
            time.sleep(40)
            
    except Exception as e:
        print(f"[ERROR] Xảy ra lỗi ngoài ý muốn trong quá trình tìm/thuê: {e}")
        time.sleep(40)
