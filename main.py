import os
import requests
import time
import json

# ====================== CẤU HÌNH GỐC NGUYÊN BẢN CỦA BẠN ======================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()
MAX_PRICE = 0.30
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
VAST_HOST = "https://vast.ai"
VAST_PATH = "/api/v1"
BASE_URL = VAST_HOST + VAST_PATH

HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

print("[START] Robot Vast.ai - Tự động thuê GPU (Đã bọc chuỗi Query)")
print(f"[INFO] Kho mã nguồn mục tiêu: {GITHUB_REPO}")

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        return r.json().get("instances", []) if r.status_code == 200 else []
    except:
        return []

def create_onstart_script():
    return f"""#!/bin/bash
apt-get update && apt-get install -y git python3-pip
rm -rf /app
git clone --depth 1 {GITHUB_DOWNLOAD_URL} /app || true
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --quiet
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
tail -f /dev/null"""

while True:
    instances = get_instances()
    active = sum(1 for i in instances if str(i.get("status","")).lower() in ["running","loading","creating","starting"])
    print(f"[CHECK] Máy đang chạy: {active}")

    # Xóa máy lỗi
    for inst in instances:
        if str(inst.get("status","")).lower() in ["error", "dead", "stopped", "failed"]:
            print("🗑️ Xóa máy lỗi")
            requests.delete(f"{BASE_URL}/instances/{inst.get('id')}/", headers=HEADERS, timeout=15)
            time.sleep(2)

    # Thuê mới nếu chưa có máy
    if active < MAX_INSTANCES:
        print("[🔍] Tìm máy RTX 3090...")
        
        # Tạo khối điều kiện lọc phần cứng nới lỏng tối đa để càn quét trúng máy rẻ
        query_filter = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "type": "ondemand",
            "dph_total": {"lte": MAX_PRICE},
            "gpu_name": {"in": ["RTX 3090"]},
            "num_gpus": {"gte": 1}
        }
        
        # BẮT BUỘC: Ép khối điều kiện thành chuỗi string gán vào biến 'q' đúng tài liệu kỹ thuật
        payload = {
            "q": json.dumps(query_filter)
        }
        
        try:
            # Gửi payload bọc chuỗi qua phương thức POST lên endpoint /bundles/
            r = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=payload, timeout=20)
            
            if r.status_code == 200:
                res_data = r.json()
                offers = res_data.get("offers", res_data.get("results", []))
                
                if offers:
                    # Sắp xếp các ưu đãi theo giá từ thấp đến cao
                    offers.sort(key=lambda x: x.get("dph_total", 999))
                    best = offers.pop(0)
                    print(f"[🎯] Thuê {best.get('gpu_name')} - Giá: {best.get('dph_total')}$")
                    
                    rent_payload = {
                        "image": "nvidia/cuda:11.7.1-runtime-ubuntu22.04",
                        "disk": 40.0,
                        "runtype": "ssh_direct",
                        "onstart": create_onstart_script()
                    }
                    
                    # Gọi chuẩn endpoint PUT /instances/{id}/ để đặt thuê máy ảo mới
                    rent_resp = requests.put(
                        f"{BASE_URL}/instances/{best['id']}/", 
                        headers=HEADERS, 
                        json=rent_payload, 
                        timeout=30
                    )
                    
                    if rent_resp.status_code in (200, 201):
                        print("[🎉] THUÊ THÀNH CÔNG!")
                        time.sleep(900)
                    else:
                        print(f"[❌] Lỗi đặt thuê từ Vast.ai (Mã lỗi: {rent_resp.status_code}): {rent_resp.text}")
                        time.sleep(30)
                else:
                    print(f"[⏳] Không có máy giá dưới {MAX_PRICE}$. Thử lại sau 1 phút...")
                    time.sleep(60)
            else:
                print(f"[❌] Máy chủ APIbundles phản hồi mã lỗi: {r.status_code} - {r.text}. Thử lại sau 1 phút...")
                time.sleep(60)
                
        except Exception as e:
            print(f"[ERROR] Lỗi hệ thống: {e}")
            time.sleep(60)
    else:
        time.sleep(120)
