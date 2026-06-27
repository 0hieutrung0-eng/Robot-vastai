import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1

BASE_URL = "https://console.vast.ai/api/v1"      # ← ĐÃ SỬA
HEADERS = {
    "Authorization": f"Bearer {VAST_API_KEY}",
    "Content-Type": "application/json"
}

GITHUB_REPO = "https://github.com/YOUR_USERNAME/YOUR_REPO.git"   # Sửa lại

def get_instances():
    try:
        r = requests.get(f"{BASE_URL}/instances/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("instances", [])
        else:
            print(f"[ERROR] API {r.status_code}: {r.text[:400]}")
            return []
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return []

# ... (phần create_onstart_script giữ nguyên như lần trước)

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

        if status in ["error", "dead", "stopped", "failed", "creating failed"]:
            print(f"   🗑️ Xóa máy lỗi: {gpu_name} (ID: {inst_id})")
            requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
            time.sleep(8)

        elif status in ACTIVE_STATUS:
            valid_kept += 1
            if valid_kept > MAX_INSTANCES:
                print(f"   🗑️ Xóa máy thừa: {gpu_name} (ID: {inst_id})")
                requests.delete(f"{BASE_URL}/instances/{inst_id}/", headers=HEADERS, timeout=15)
                time.sleep(8)

    if valid_kept >= MAX_INSTANCES:
        print(f"[✅] Đã có {valid_kept} máy ổn định → Nghỉ 8 phút")
        time.sleep(480)
        continue

    # Phần tìm và thuê giữ nguyên (chỉ BASE_URL là v1)
    print("[🔍] Đang tìm máy RTX 3090...")
    # ... (search_payload và rent_payload giữ như cũ)
