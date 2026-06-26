import requests
import time

# --- CẤU HÌNH THÔNG SỐ CỦA BẠN ---
VAST_API_KEY = "fdf12c0dad8dc53d40e18bd0ebfd39834f46944396b697e4d173a1418476f219"
MAX_PRICE = 0.15  # Giá trần mong muốn ($/giờ)

# Địa chỉ API gốc của Vast.ai
BASE_URL = "https://vast.ai"
headers = {"Accept": "application/json", "Authorization": f"Bearer {VAST_API_KEY}"}

print("[START] Khởi động robot săn GPU phổ thông cào dữ liệu AI 24/7...")

while True:
    try:
        print(f"\n[INFO] Đang quét Vast.ai vào lúc: {time.strftime('%X')}...")

        # 1. TÌM KIẾM MÁY PHÙ HỢP
        search_url = f"{BASE_URL}/bundle/"
        # Cấu hình bộ lọc tìm kiếm theo đúng chuẩn API của Vast.ai
        search_payload = {
            "q": f"rentprice < {MAX_PRICE} inet_down > 600 reliability > 0.90 cuda_vers >= 11.8 rented=false",
            "order": [["rentprice", "asc"]],
        }

        response = requests.post(search_url, headers=headers, json=search_payload)

        if response.status_code == 200:
            offers = response.json().get("offers", [])

            if offers:
                best_offer = offers[0]
                instance_id = best_offer["id"]
                actual_price = best_offer["rentprice"]
                print(
                    f"[OK] Tìm thấy GPU giá rẻ! ID: {instance_id} (Giá: {actual_price}$/h). Đang tự động thuê..."
                )

                # 2. TIẾN HÀNH THUÊ MÁY VÀ KHỞI CHẠY KHÔNG GIAN DOCKER
                # Tối ưu: Đưa thẳng Docker image và biến môi trường của Bot vào lúc tạo máy
                rent_url = f"{BASE_URL}/asks/{instance_id}/"
                rent_payload = {
                    "image": "gradients/scraper-agent:latest",  # Dùng thẳng ảnh bot của bạn
                    "env": {
                        "TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
                    },  # Truyền token ví của bạn
                    "disk": 10.0,  # Dung lượng ổ đĩa cấp cho máy (GB)
                }

                rent_res = requests.put(
                    rent_url, headers=headers, json=rent_payload
                )

                if rent_res.status_code == 200:
                    print(
                        "[🎉] THUÊ THÀNH CÔNG! Máy ảo đang khởi động và tự kích hoạt Bot cào dữ liệu ngầm."
                    )
                else:
                    print(
                        f"[X] Thuê thất bại. Mã lỗi API: {rent_res.status_code} - {rent_res.text}"
                    )
            else:
                print("[X] Chưa có GPU cỏ có giá và cấu hình phù hợp.")
        else:
            print(f"[X] Lỗi truy vấn kho máy: {response.status_code}")

    except Exception as e:
        print(f"[ERROR] Gặp lỗi hệ thống: {e}")

    # Chờ 5 phút (300 giây) trước khi quét lượt tiếp theo để tránh bị khóa API do spam
    time.sleep(300)
