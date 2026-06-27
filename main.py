import os
import requests
import time
import json
import threading
import urllib.parse
from fastapi import FastAPI
import uvicorn

# ==============================================================================
# PHẦN 1: KHỞI TẠO MÁY CHỦ WEB BẮT BUỘC ĐỂ GIỮ HUGGING FACE SPACES LUÔN "RUNNING"
# ==============================================================================
app = FastAPI()
SYSTEM_STATUS = "Robot đang chạy chế độ Brute-force chẩn đoán..."

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
BASE_URL = "https://console.vast.ai/api/v1/instances/"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

print_and_log("[START] Robot Vast.ai v1 - Quét Sạch Mọi Định Dạng Tham Số q")

if not VAST_API_KEY:
    print_and_log("[❌] LỖI CẤU HÌNH: Thiếu VAST_API_KEY!")
    while True:
        time.sleep(3600)


# ==============================================================================
# PHẦN 2: DANH SÁCH MỌI KIỂU ĐỊNH DẠNG Q CÓ THỂ XẢY RA TRÊN ĐỜI
# ==============================================================================
# Cấu trúc 1: Chuỗi JSON chuẩn hóa URL (Toán tử lồng)
q1 = json.dumps({"verified": {"eq": True}, "external": {"eq": False}, "rentable": {"eq": True}, "rented": {"eq": False}}, separators=(',', ':'))

# Cấu trúc 2: Chuỗi JSON làm phẳng (Không toán tử)
q2 = json.dumps({"verified": True, "external": False, "rentable": True, "rented": False}, separators=(',', ':'))

# Cấu trúc 3: Truyền thẳng tên GPU vào query search text
q3 = json.dumps({"gpu_name": {"eq": "GeForce RTX 3090"}}, separators=(',', ':'))

# Cấu trúc 4: Định dạng mảng hoặc chuỗi text tìm kiếm tự do
q4 = "GeForce RTX 3090"

# Cấu trúc 5: Thử bọc thêm wrapper Object bên ngoài
q5 = json.dumps({"q": {"verified": True, "rentable": True, "rented": False}}, separators=(',', ':'))

# Cấu trúc 6: Chuỗi filter rút gọn tối đa
q6 = json.dumps({"rentable": True, "rented": False}, separators=(',', ':'))

tests = [
    {"desc": "Kiểu 1: GET Object toán tử lồng (Mã hóa URL)", "params": {"q": q1, "api_key": VAST_API_KEY}},
    {"desc": "Kiểu 2: GET Object phẳng (Mã hóa URL)", "params": {"q": q2, "api_key": VAST_API_KEY}},
    {"desc": "Kiểu 3: GET Chỉ lọc chính xác tên GPU 3090", "params": {"q": q3, "api_key": VAST_API_KEY}},
    {"desc": "Kiểu 4: GET Truyền text thuần (Search query)", "params": {"q": q4, "api_key": VAST_API_KEY}},
    {"desc": "Kiểu 5: GET Bọc wrapper q bên trong q", "params": {"q": q5, "api_key": VAST_API_KEY}},
    {"desc": "Kiểu 6: GET Thả lỏng bộ lọc chỉ check rentable/rented", "params": {"q": q6, "api_key": VAST_API_KEY}},
    {"desc": "Kiểu 7: GET Truyền dạng mảng tham số phẳng trực tiếp vào URL", "params": {"verified": "true", "external": "false", "rentable": "true", "rented": "false", "api_key": VAST_API_KEY}}
]


# ==============================================================================
# PHẦN 3: VÒNG LẶP THỬ NGHIỆM LIÊN TỤC
# ==============================================================================
while True:
    print_and_log("\n" + "="*70)
    print_and_log("[🔍] KÍCH HOẠT CHU KỲ KIỂM TRA TOÀN DIỆN CÁC KIỂU THAM SỐ...")
    print_and_log("="*70)
    
    for idx, case in enumerate(tests, 1):
        print_and_log(f"\n👉 [TEST {idx}] Thử nghiệm: {case['desc']}")
        try:
            # Gửi request với các kiểu build params khác nhau
            r = requests.get(BASE_URL, headers=HEADERS, params=case["params"], timeout=15)
            
            print_and_log(f"  -> Trạng thái HTTP: {r.status_code}")
            
            if r.status_code == 200:
                res_json = r.json()
                total = res_json.get("total_instances", res_json.get("instances_found", "N/A"))
                instances_len = len(res_json.get("instances", [])) if isinstance(res_json.get("instances"), list) else "N/A"
                
                print_and_log(f"  -> 🎉 THÀNH CÔNG KHỚP ENDPOINT!")
                print_and_log(f"  -> Kết quả dữ liệu: total_instances = {total} | Số lượng máy trong mảng = {instances_len}")
                
                # Nếu tìm thấy máy thật, in thử 300 ký tự đầu để xem cấu trúc
                if instances_len != "N/A" and instances_len > 0:
                    print_and_log(f"  -> 🎯 ĐÃ TÌM THẤY ĐÚNG ĐỊNH DẠNG! Mẫu dữ liệu thô:")
                    print(f"{r.text[:400]}...", flush=True)
            else:
                print_and_log(f"  -> ❌ Thất bại. Nội dung phản hồi: {r.text[:150]}")
                
        except Exception as e:
            print_and_log(f"  -> Lỗi kết nối vật lý: {e}")
            
    print_and_log("\n" + "-"*70)
    print_and_log("[💡] Đã hoàn thành 1 chu kỳ thử nghiệm cuốn chiếu. Đợi 60 giây...")
    time.sleep(60)
