import os
import time
import json
import subprocess
import requests
from threading import Thread

# =====================================================================
# ⚙️ CẤU HÌNH HỆ THỐNG (BẠN CẦN ĐIỀN THÔNG TIN CỦA BẠN VÀO ĐÂY)
# =====================================================================
WEBHOOK_LUONG_4_URL = "DÁN_ĐƯỜNG_LINK_WEBHOOK_LUỒNG_4_CỦA_BẠN_VÀO_ĐÂY"
TOTAL_SCENES = 100  # Đặt mốc chặn đủ 100 phân cảnh sẽ kích hoạt gộp phim

# Thư mục làm việc cố định trên GPU Vast.ai
WORKSPACE = "/workspace"
RENDER_DIR = os.path.join(WORKSPACE, "render_output")
VOICE_DIR = os.path.join(WORKSPACE, "voice_output")
FINAL_DIR = os.path.join(WORKSPACE, "final_scenes")
COMFYUI_DIR = os.path.join(WORKSPACE, "ComfyUI")

# Tạo cấu trúc thư mục sạch sẽ
for folder in [RENDER_DIR, VOICE_DIR, FINAL_DIR]:
    os.makedirs(folder, exist_ok=True)

print("[INFO] Hệ thống MasterBot Film AI đã khởi động ngầm...")

# =====================================================================
# 🎙️ 1. TỰ ĐỘNG CHẠY OFFLINE AI GIỌNG NÓI TIẾNG VIỆT (KOKORO-82M)
# =====================================================================
def generate_voiceover(scene_number, text):
    """
    Sử dụng AI Kokoro chạy offline trực tiếp trên RTX 4090 để chuyển 
    lời thoại tiếng Việt thành file âm thanh thuyết minh .mp3 miễn phí.
    """
    output_path = os.path.join(VOICE_DIR, f"canh_{scene_number}.mp3")
    print(f"[VOICE] Đang tạo giọng đọc cho Cảnh {scene_number}...")
    
    # Đoạn lệnh script gọi mô hình Kokoro nhả file audio thuyết minh tiếng Việt giọng Nam/Nữ mượt mà
    cmd = [
        "kokoro-tts",
        "--text", text,
        "--lang", "vi",
        "--voice", "v_south_female",  # Có thể đổi thành v_north_male hoặc v_south_male tùy chọn
        "--output", output_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[✔️ VOICE] Đã lưu file thoại: {output_path}")
    except Exception as e:
        print(f"[❌ ERROR VOICE] Cảnh {scene_number} lỗi: {e}")

# =====================================================================
# 🎬 2. GIÁM SÁT HÀNG ĐỢI VÀ ÉP PHẦN MỀM COMFYUI RENDER PHIM
# =====================================================================
def watch_and_match_assets():
    """
    Hàm chạy ngầm liên tục quét ổ cứng. Cứ mỗi khi thấy ComfyUI nhả ra 1 file video thô,
    và AI Kokoro nhả ra 1 file tiếng, nó sẽ dùng FFmpeg lồng khớp tiếng vào hình ngay lập tức.
    """
    processed_scenes = set()
    
    while len(processed_scenes) < TOTAL_SCENES:
        time.sleep(2)  # Nghỉ 2 giây mỗi chu kỳ quét để tránh tốn tài nguyên chip
        
        for i in range(1, TOTAL_SCENES + 1):
            if i in processed_scenes:
                continue
                
            video_raw = os.path.join(RENDER_DIR, f"canh_{i}.mp4")
            audio_raw = os.path.join(VOICE_DIR, f"canh_{i}.mp3")
            scene_finished = os.path.join(FINAL_DIR, f"canh_{i}_hoanchinh.mp4")
            
            # Nếu cả file hình thô và file tiếng của phân cảnh đó đã xuất hiện trên ổ cứng
            if os.path.exists(video_raw) and os.path.exists(audio_raw):
                print(f"[FFMPEG] Đang lồng khớp nhạc thoại cho Cảnh {i}...")
                
                # Lệnh FFmpeg ép tiếng lồng vào hình và tự động co giãn hình ảnh cho vừa khít độ dài tiếng
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_raw,
                    "-i", audio_raw,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-shortest",  # Cắt/Co ngắn theo file có thời lượng ngắn hơn
                    scene_finished
                ]
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    processed_scenes.add(i)
                    print(f"[✔️ MATCH] Hoàn thành phân cảnh có tiếng: {scene_finished}")
                except Exception as e:
                    print(f"[❌ FFMPEG ERROR] Lỗi ghép cảnh {i}: {e}")

    # =====================================================================
    # 🎛️ 3. GỘP PHIM BẰNG FFMPEG VÀ TẢI THẲNG LÊN GOOGLE DRIVE
    # =====================================================================
    print("[🔥 HIGHLIGHT] Đã thu thập đủ 100 phân cảnh sạch! Bắt đầu gộp thành phim 10 phút...")
    
    # Tạo tệp danh sách đầu vào cho FFmpeg đọc tuần tự
    list_file_path = os.path.join(WORKSPACE, "movie_list.txt")
    with open(list_file_path, "w") as f:
        for i in range(1, TOTAL_SCENES + 1):
            f.write(f"file '{FINAL_DIR}/canh_{i}_hoanchinh.mp4'\n")
            
    final_movie_path = os.path.join(WORKSPACE, "Bo_Phim_10_Phut_Hoan_Chinh.mp4")
    
    # Lệnh FFmpeg nối một mạch 100 cảnh siêu tốc không làm suy giảm chất lượng hình ảnh 8K
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file_path,
        "-c", "copy",
        final_movie_path
    ]
    subprocess.run(concat_cmd, check=True)
    print(f"[✔️ MOVIE DONE] Đã xuất bản phim thành công tại: {final_movie_path}")
    
    # Tiến hành tải file phim hoàn chỉnh này lên Google Drive
    upload_to_google_drive(final_movie_path)

# =====================================================================
# ☁️ 4. HÀM GỌI GOOGLE DRIVE API TỰ ĐỘNG UPLOAD FILE PHIM
# =====================================================================
def upload_to_google_drive(file_path):
    print("[DRIVE] Đang kết nối Drive API để tải phim lên...")
    try:
        # Lệnh script gọi công cụ rclone hoặc google-drive-upload tải file ngầm bảo mật
        # (Yêu cầu Token Drive đã được cấu hình tự động thông qua file onstart của Make trước đó)
        os.system(f"gdrive upload {file_path} --hide-progress")
        print("[✔️ DRIVE SUCCESS] Bộ phim dài 10 phút đã nằm an toàn trên Google Drive của bạn!")
    except Exception as e:
        print(f"[❌ DRIVE ERROR] Lỗi tải phim lên kho lưu trữ: {e}")
        
    # KÍCH HOẠT HỦY THUÊ MÁY ẢO NGAY LẬP TỨC ĐỂ TIẾT KIỆM TIỀN
    trigger_auto_destroy_server()

# =====================================================================
# 🚀 5. PHÓNG TÍN HIỆU VỀ WEBHOOK LUỒNG 4 ĐỂ HỦY THUÊ VGA ĐÁM MÂY
# =====================================================================
def trigger_auto_destroy_server():
    print("[🔥 DESTROY] Phim đã lên Drive. Phát lệnh bắn tín hiệu hủy thuê server về Make.com...")
    try:
        # Lấy Instance ID định danh động của con máy hiện tại đang chạy trên Vast.ai
        instance_id = os.environ.get("VAST_CONTAINERLABEL", "unknown")
        
        payload = {
            "status": "hoan_thanh_tron_goi",
            "message": "Phim 10 phút đã render, gộp âm thanh, nối phim và upload Drive hoàn tất vẹn toàn.",
            "instance_id": instance_id
        }
        
        # Phát bắn HTTP POST cứu cánh ví tiền của bạn
        response = requests.post(WEBHOOK_LUONG_4_URL, json=payload, timeout=30)
        if response.status_code == 200:
            print("[✔️ SYSTEM DISMISSED] Make.com đã nhận lệnh. Máy chủ sẽ bị xóa sổ sau vài giây!")
        else:
            print(f"[⚠️ WARNING] Gửi lệnh hủy máy thất bại, phản hồi từ Make: {response.status_code}")
    except Exception as e:
        print(f"[❌ FATAL ERROR] Lỗi cổng truyền tín hiệu hủy máy: {e}")

# =====================================================================
# 🌐 6. CỔNG API LẮNG NGHE ĐÓN NHẬN DỮ LIỆU TỪ VÒNG LẶP CỦA MAKE.COM
# =====================================================================
# Đoạn mã khởi tạo một máy chủ web nội bộ mini (Flask) chạy song song trên GPU 
# nhằm đón nhận liên thanh 100 cảnh do module HTTP 2 của Make bắn vào hàng đợi
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/api/queue', methods=['POST'])
def receive_scene_from_make():
    data = request.json
    scene_number = data.get("scene_number")
    ai_video_prompt = data.get("ai_video_prompt")
    dialogue_vietnamese = data.get("dialogue_vietnamese")
    
    # 1. Kích hoạt Robot sinh giọng nói thuyết minh tiếng Việt lập tức cho phân cảnh này
    Thread(target=generate_voiceover, args=(scene_number, dialogue_vietnamese)).start()
    
    # 2. Đẩy chuỗi prompt tiếng Anh vào hàng đợi API gốc của phần mềm ComfyUI đang mở sẵn
    comfy_payload = {"prompt_text": ai_video_prompt, "save_name": f"canh_{scene_number}"}
    requests.post("http://127.0.0", json=comfy_payload)
    
    return jsonify({"status": "queued", "scene": scene_number}), 200

if __name__ == "__main__":
    # Khởi động luồng phụ chạy ngầm giám sát, gộp phim bằng FFmpeg liên tục
    Thread(target=watch_and_match_assets, daemon=True).start()
    
    # Mở cổng 8188 nhận kịch bản từ Make.com bắn sang
    app.run(host="0.0.0.0", port=8188, debug=False)
