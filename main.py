import requests
import time
import sys

VAST_API_KEY = "fdf12c0dad8dc53d40e18bd0ebfd39834f46944396b697e4d173a1418476f219"
MAX_PRICE = 0.35  # Giá tối đa ($/giờ)
IONET_TOKEN = "mkdir -p ~/.nosana && echo '3gvwvPnSfDSR4DhA5KHPkdj9Yz3tKVmnMoXDXd3GU7Hc6fZe3zDZGfEF2P4DtNSuUu9SyUQVCDNUm3dL5AzFeFcD' > ~/.nosana/private.json && docker run -d --pull=always --gpus=all --name nosana-node --network host --volume /root/.nosana/:/root/.nosana/ nosana/nosana-node:latest start --network mainnet"

headers = {"Authorization": f"Bearer {VAST_API_KEY}"}

print("[START] Khoi dong robot san RTX 4090 tu dong 24/7...")

while True:
    try:
        print(f"\n[INFO] Dang quet Vast.ai vao luc: {time.strftime('%X')}...")
        
        # 1. Sửa lỗi đường dẫn quét tìm máy chuẩn API Vast.ai
        query = f"gpu_name == 'RTX 4090' rentprice < {MAX_PRICE} inet_down > 500 reliability > 0.99 cuda_vers >= 12.0"
        url = f"https://vast.ai{query}&order=rentprice"
        
        response = requests.get(url, headers=headers).json()
        offers = response.get("offers", [])
        
        if offers:
            # Sửa lỗi lấy phần tử đầu tiên trong danh sách máy tìm được
            best_offer = offers[0]
            instance_id = best_offer["id"]
            print(f"[OK] Tim thay may! ID: {instance_id}. Dang tu dong thue...")
            
            # 2. Sửa lỗi đường dẫn bấm thuê máy
            rent_url = f"https://vast.ai{instance_id}/"
            rent_res = requests.put(rent_url, headers=headers, json={"image": "pytorch/pytorch:latest"})
            
            if rent_res.status_code == 200:
                print("[⏳] Thue thanh cong. Cho 2 phut de may ao khoi dong...")
                time.sleep(120)
                
                # 3. Sửa lỗi đường dẫn gửi lệnh kích hoạt Nosana qua SSH API
                ssh_url = f"https://vast.ai{instance_id}/command/"
                payload = {"command": f"screen -dmS nosana-job bash -c '{IONET_TOKEN}'"}
                requests.post(ssh_url, headers=headers, json=payload)
                print("[🎉] DA KET NOI NOSANA! Robot tiep tuc quet de san them may...")
            else:
                print(f"[X] Thue may that bai. Ma loi: {rent_res.status_code}")
                
        else:
            print("[X] Chua co may gia re phu hop.")
            
    except Exception as e:
        print(f"[ERROR] Gap loi he thong: {e}")
        
    # Nghỉ đúng 5 phút (300 giây) rồi tự động lặp lại quy trình
    time.sleep(300)
