import os
import time
import json
import subprocess
import requests
import queue
from threading import Thread
from flask import Flask, request, jsonify

# =====================================================================
# ⚙️ CẤU HÌNH HỆ THỐNG (THAY LINK WEBHOOK CỦA BẠN VÀO ĐÂY)
# =====================================================================
WEBHOOK_LUONG_4_URL = "https://hook.eu1.make.com/jtre43qr5lprxrkb4nme9fn4haexyoxc"
TOTAL_SCENES = 100  

WORKSPACE = "/workspace"
RENDER_DIR = os.path.join(WORKSPACE, "render_output")
VOICE_DIR = os.path.join(WORKSPACE, "voice_output")
FINAL_DIR = os.path.join(WORKSPACE, "final_scenes")

for folder in [RENDER_DIR, VOICE_DIR, FINAL_DIR]:
    os.makedirs(folder, exist_ok=True)

# Khởi tạo Hàng đợi xử lý tuần tự (Xếp hàng chống sập GPU)
task_queue = queue.Queue()

print("[INFO] Hệ thống MasterBot Film AI với Hàng đợi tuần tự đang chạy...")

# =====================================================================
# 🛠️ LUỒNG XỬ LÝ TUẦN TỰ KHÉP KÍN (WORKER THREAD)
# =====================================================================
def process_queue_worker():
    """Luồng chạy ngầm bốc từng cảnh ra xử lý trọn gói, xong cảnh này mới làm cảnh sau"""
    processed_count = 0
    
    while True:
        task = task_queue.get()
        if task is None:
            break
            
        scene_number = task["scene_number"]
        ai_video_prompt = task["ai_video_prompt"]
        dialogue_vietnamese = task["dialogue_vietnamese"]
        
        print(f"\n[QUEUE] 🎬 Bắt đầu xử lý trọn gói Cảnh {scene_number}/{TOTAL_SCENES}...")
        
        audio_path = os.path.join(VOICE_DIR, f"canh_{scene_number}.mp3")
        video_path = os.path.join(RENDER_DIR, f"canh_{scene_number}.mp4")
        scene_finished = os.path.join(FINAL_DIR, f"canh_{scene_number}_hoanchinh.mp4")

        # --- BƯỚC 1: SINH GIỌNG NÓI TIẾNG VIỆT (KOKORO AI) ---
        voice_cmd = ["kokoro-tts", "--text", dialogue_vietnamese, "--lang", "vi", "--voice", "v_south_female", "--output", audio_path]
        try:
            subprocess.run(voice_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[✔️ 1. VOICE] Đã tạo xong file Audio cho Cảnh {scene_number}")
        except Exception as e:
            print(f"[❌ VOICE ERROR] Lỗi tạo tiếng Cảnh {scene_number}: {e}")

        # --- BƯỚC 2: GỬI LỆNH RENDER VIDEO SANG COMFYUI ---
        comfy_payload = {"prompt_text": ai_video_prompt, "save_name": f"canh_{scene_number}"}
        try:
            # Gửi lệnh vào API của ComfyUI (Giả định ComfyUI chạy cổng nội bộ 8189)
            requests.post("http://127.0.0.1:8189/prompt", json=comfy_payload, timeout=10)
            print(f"[COMFYUI] Đã đẩy lệnh render vào ComfyUI. Chờ sinh file video...")
            
            # Vòng lặp tối ưu: Treo luồng chờ cho đến khi thấy file video thật xuất hiện trên ổ cứng
            while not os.path.exists(video_path):
                time.sleep(3)
            print(f"[✔️ 2. VIDEO] Đã tìm thấy file Video từ ComfyUI cho Cảnh {scene_number}")
        except Exception as e:
            print(f"[❌ COMFYUI ERROR] Cảnh {scene_number} lỗi kết nối API: {e}")

        # --- BƯỚC 3: GHÉP HÌNH VỚI TIẾNG BẰNG FFMPEG (CUỐN CHIẾU) ---
        if os.path.exists(video_path) and os.path.exists(audio_path):
            ffmpeg_cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path, "-c:v", "libx264", "-c:a", "aac", "-shortest", scene_finished]
            try:
                subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[✔️ 3. MATCH] Đã xuất bản phân cảnh khớp tiếng: {scene_finished}")
                processed_count += 1
            except Exception as e:
                print(f"[❌ FFMPEG ERROR] Lỗi ghép trục Cảnh {scene_number}: {e}")
        else:
            print(f"[❌ MATCH FAILED] Thiếu nguyên liệu hình/tiếng của Cảnh {scene_number}, bỏ qua ghép nối.")
        
        # Giải phóng phần tử trong hàng đợi
        task_queue.task_done()
        
        # KIỂM TRA MỐC HOÀN THÀNH: Đủ 100 cảnh thì tự động kích hoạt gộp phim tổng
        if processed_count == TOTAL_SCENES:
            trigger_build_final_movie()

# =====================================================================
# 🎛️ NỐI PHIM TỔNG & TẢI LÊN GOOGLE DRIVE
# =====================================================================
def trigger_build_final_movie():
    print("\n[🔥 SYSTEM] Đã thu thập đủ 100 phân cảnh sạch! Tiến hành nối chuỗi thành phim 10 phút...")
    
    list_file_path = os.path.join(WORKSPACE, "movie_list.txt")
    with open(list_file_path, "w") as f:
        for i in range(1, TOTAL_SCENES + 1):
            f.write(f"file '{FINAL_DIR}/canh_{i}_hoanchinh.mp4'\n")
            
    video_name = f"Phim_AI_10_Phut_{int(time.time())}.mp4"
    final_movie_path = os.path.join(WORKSPACE, video_name)
    
    concat_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file_path, "-c", "copy", final_movie_path]
    try:
        subprocess.run(concat_cmd, check=True)
        print(f"[✔️ MOVIE DONE] Phim tổng đã xuất bản tại: {final_movie_path}")
        
        # Tải thẳng lên Google Drive
        print("[DRIVE] Đang đẩy video lên trạm trung chuyển Google Drive...")
        os.system(f"gdrive upload {final_movie_path} --hide-progress")
        print("[✔️ DRIVE SUCCESS] Video đã nằm an toàn trên Google Drive!")
        
        # Phát tín hiệu về Luồng 4 trên Make để up YouTube và hủy máy
        trigger_make_webhook(video_name)
    except Exception as e:
        print(f"[❌ FATAL] Lỗi quy trình xuất bản phim tổng hợp: {e}")

def trigger_make_webhook(video_name):
    print("[🔥 DESTROY] Phát tín hiệu hoàn thành về Luồng 4 trên Make.com...")
    try:
        instance_id = os.environ.get("VAST_CONTAINERLABEL", "unknown")
        payload = {
            "status": "render_done",
            "video_name": video_name,
            "instance_id": instance_id
        }
        requests.post(WEBHOOK_LUONG_4_URL, json=payload, timeout=30)
        print("[✔️ SYSTEM] Đã bắn Webhook thành công! Máy ảo sẵn sàng nhận lệnh xóa.")
    except Exception as e:
        print(f"[❌ WEBHOOK ERROR] Không thể phát tín hiệu hủy máy: {e}")

# =====================================================================
# 🌐 CỔNG API TIẾP NHẬN 100 CẢNH LIÊN THANH TỪ MAKE.COM
# =====================================================================
app = Flask(__name__)

@app.route('/api/queue', methods=['POST'])
def receive_scene_from_make():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
        
    # Đón nhận dữ liệu tốc độ cao từ Make và xếp thẳng vào hàng đợi an toàn
    task_queue.put({
        "scene_number": data.get("scene_number"),
        "ai_video_prompt": data.get("ai_video_prompt"),
        "dialogue_vietnamese": data.get("dialogue_vietnamese")
    })
    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    # Khởi động luồng xử lý tuần tự chạy ngầm độc lập
    Thread(target=process_queue_worker, daemon=True).start()
    
    # Mở cổng 8188 nhận kịch bản từ Make.com bắn sang
    app.run(host="0.0.0.0", port=8188, debug=False)
