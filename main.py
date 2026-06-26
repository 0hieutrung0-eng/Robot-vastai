import requests
import time
import json

# --- CẤU HÌNH THÔNG SỐ ---
VAST_API_KEY = "fdf12c0dad8dc53d40e18bd0ebfd39834f46944396b697e4d173a1418476f219"
MAX_PRICE = 0.15  # Giá trần tối đa ($/giờ)

BASE_URL = "https://vast.ai"
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {VAST_API_KEY}"
}

print("[START] Khởi động robot săn GPU phổ thông cào dữ liệu AI 24/7...")

while True:
    try:
        print(f"\n[INFO] Đang quét Vast.ai vào lúc: {time.strftime('%X')}...")

        # 1. TÌM KIẾM MÁY PHÙ HỢP
        search_url = f"{BASE_URL}/bundles/"
        search_payload = {
            "q": f"rentprice < {MAX_PRICE} inet_down > 600 reliability > 0.90 cuda_vers >= 11.8 rented=false",
            "order": [["rentprice", "asc"]]
        }
        
        # SỬA CHUẨN: Ép kiểu dữ liệu sang chuỗi JSON thuần túy bằng json.dumps và truyền qua tham số data=
        response = requests.post(search_url, headers=headers, data=json.dumps(search_payload))

        if response.status_code == 200:
            offers = response.json().get("offers", [])

            if offers:
                # Lấy phần tử index số 0 trong danh sách kết quả trả về
                best_offer = offers[0] 
                offer_id = best_offer["id"]
                actual_price = best_offer["rentprice"]
                print(f"[OK] Tìm thấy GPU giá rẻ! ID Lượt chào: {offer_id} (Giá: {actual_price}$/h). Đang tự động thuê...")

                # 2. TIẾN HÀNH THUÊ MÁY
                rent_url = f"{BASE_URL}/asks/{offer_id}/"
                rent_payload = {
                    "image": "gradients/scraper-agent:latest",
                    "env": {
                        "TOKEN": "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3"
                    },
                    "disk": 10.0,
                    "runtype": "args"
                }

                rent_res = requests.post(rent_url, headers=headers, data=json.dumps(rent_payload))

                if rent_res.status_code == 200:
                    result_data = rent_res.json()
                    instance_id = result_data.get("new_contract", "Không rõ ID")
                    print(f"[🎉] THUÊ THÀNH CÔNG! Mã hợp đồng thực thể mới: {instance_id}")
                else:
                    print(f"[X] Thuê thất bại. Mã lỗi API: {rent_res.status_code} - {rent_res.text}")
            else:
                print("[X] Chưa tìm thấy máy cấu hình phổ thông nào phù hợp với mức giá yêu cầu.")
        else:
            print(f"[X] Lỗi truy vấn kho máy. Mã trạng thái HTTP: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[💥 CRASH] Gặp lỗi logic phần mềm hoặc kết nối: {type(e).__name__} - {e}")

    # Chờ 5 phút trước khi thực hiện chu kỳ quét tiếp theo
    time.sleep(300)
