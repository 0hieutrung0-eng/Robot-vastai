import requests
import time

# --- CẤU HÌNH THÔNG SỐ CỦA BẠN ---
VAST_API_KEY = "fdf12c0dad8dc53d40e18bd0ebfd39834f46944396b697e4d173a1418476f219"
MAX_PRICE = 0.15 # CHỈ thuê card rẻ (RTX 3060/3070) giá dưới 0.08$/giờ để tối ưu gốc

# LỆNH CHẠY BOT CÀO DATA AI (Thay ĐOẠN_MÃ_TOKEN_TÀI_KHOẢN bằng mã ví hoặc token của bạn trên chợ Data)
DATA_BOT_TOKEN = "docker run -d --name ai-scraper-node -e TOKEN='rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3' --network host --gpus all gradients/scraper-agent:latest"

headers = {"Authorization": f"Bearer {VAST_API_KEY}"}
print("[START] Khoi dong robot san GPU pho thong cao du lieu AI 24/7...")

while True:
    try:
        print(f"\n[INFO] Dang quet Vast.ai vao luc: {time.strftime('%X')}...")
        
        # Chỉ quét các dòng card cỏ, giá cực rẻ nhưng mạng phải khỏe để cào data nhanh
        query = f"rentprice < {MAX_PRICE} inet_down > 600 reliability > 0.98 cuda_vers >= 11.8"
        url = f"https://vast.ai{query}&order=rentprice"
        
        response = requests.get(url, headers=headers).json()
        offers = response.get("offers", [])
        
        if offers:
            best_offer = offers[0]
            instance_id = best_offer["id"]
            print(f"[OK] Tim thay GPU gia re! ID: {instance_id}. Dang tu dong thue...")
            
            rent_url = f"https://vast.ai{instance_id}/"
            rent_res = requests.put(rent_url, headers=headers, json={"image": "pytorch/pytorch:latest"})
            
            if rent_res.status_code == 200:
                print("[⏳] Thue thanh cong. Cho 2 phut de may ao khoi dong...")
                time.sleep(120)
                
                # Bắn lệnh kích hoạt Bot cào dữ liệu ngầm vào máy ảo Vast.ai
                ssh_url = f"https://vast.ai{instance_id}/command/"
                payload = {"command": f"screen -dmS datacrawl bash -c '{DATA_BOT_TOKEN}'"}
                requests.post(ssh_url, headers=headers, json=payload)
                print("[🎉] BOT CÀO DATA ĐÃ CHẠY! Đang tu dong thu thap va ban du lieu kiem USD...")
            else:
                print(f"[X] Thue that bai: {rent_res.status_code}")
        else:
            print("[X] Chưa có GPU cỏ giá phù hợp.")
            
    except Exception as e:
        print(f"[ERROR] Gap loi he thong: {e}")
        
    time.sleep(300) # Cứ 5 phút quét săn thêm máy 1 lần
