import requests
import time

# --- CẤU HÌNH THÔNG SỐ ---
VAST_API_KEY = "fdf12c0dad8dc53d40e18bd0ebfd39834f46944396b697e4d173a1418476f219"
MAX_PRICE = 0.15  # Giá trần tối đa ($/giờ)

# Địa chỉ API chuẩn của bảng điều khiển Vast.ai
BASE_URL = "https://console.vast.ai/api/v0"
headers = {
    "Accept": "application/json", 
    "Authorization": f"Bearer {VAST_API_KEY}"
}

print("[START] Khởi động robot săn GPU phổ thông cào dữ liệu AI 24/7...")

while True:
    try:
        print(f"\n[INFO] Đang quét Vast.ai vào lúc: {time.strftime('%X')}...")

        # 1. TÌM KIẾM MÁY PHÙ HỢP (ENDPOINT CHUẨN: /bundles/)
        search_url = f"{BASE_URL}/bundles/"
        
        # Cấu hình bộ lọc tìm kiếm chính xác theo JSON Schema của Vast.ai
        search_payload = {
            "q": {
                "rentprice": {"lt": MAX_PRICE},
                "inet_down": {"gt": 600},
                "reliability": {"gt": 0.90},
                "cuda_vers": {"gte": 11.8},
                "rented": {"eq": False}
            },
            "order": [["rentprice", "asc"]]
        }

        response = requests.post(search_url, headers=headers, json=search_payload)

        if response.status_code == 200:
            # API trả về danh sách các gói máy (offers) thỏa mãn điều kiện
            offers = response.json().get("offers", [])

            if offers:
                best_offer = offers[0]
                offer_id = best_offer["id"]
                actual_price = best_offer["rentprice"]
                print(f"[OK] Tìm thấy GPU giá rẻ! ID Lượt chào: {offer_id} (Giá: {actual_price}$/h). Đang tự động thuê...")

                # 2. TIẾN HÀNH THUÊ MÁY (ENDPOINT CHUẨN: POST /asks/{offer_id}/)
                rent_url = f"{BASE_URL}/asks/{offer_id}/"
                rent_payload = {
                    "image": "gradients/scraper-agent:latest",  # Docker image chạy Bot cào dữ liệu
                    "env": {
                        "TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
                    },  # Biến môi trường truyền token ví
                    "disk": 10.0,  # Cấp phát 10GB ổ đĩa cho máy ảo
                    "runtype": "args"  # Chế độ chạy mặc định cho Docker image
                }

                # Sử dụng POST thay vì PUT để khởi tạo thực thể mới từ chào giá
                rent_res = requests.post(rent_url, headers=headers, json=rent_payload)

                if rent_res.status_code == 200:
                    result_data = rent_res.json()
                    instance_id = result_data.get("new_contract", "Không rõ ID")
                    print(f"[🎉] THUÊ THÀNH CÔNG! Mã hợp đồng thực thể mới: {instance_id}")
                    print("[INFO] Hệ thống đang tải Docker và tự kích hoạt Bot cào dữ liệu ngầm.")
                else:
                    print(f"[X] Thuê thất bại. Mã lỗi API: {rent_res.status_code} - {rent_res.text}")
            else:
                print("[X] Chưa tìm thấy máy cấu hình phổ thông nào phù hợp với mức giá yêu cầu.")
        else:
            print(f"[X] Lỗi truy vấn kho máy. Mã trạng thái HTTP: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[ERROR] Gặp lỗi kết nối hoặc xử lý hệ thống: {e}")

    # Chờ 5 phút (300 giây) để thực hiện chu kỳ quét tiếp theo
    time.sleep(300)
