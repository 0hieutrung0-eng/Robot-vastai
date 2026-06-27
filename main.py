import os
import requests
import time

VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "rayon_omRkJmRpmrtrZhAySsjpSsQfu1PKXcN3").strip()

MAX_PRICE = 0.30
MAX_INSTANCES = 1
BASE_URL = "https://console.vast.ai/api/v1"
HEADERS = {"Authorization": f"Bearer {VAST_API_KEY}", "Content-Type": "application/json"}

GITHUB_REPO = "https://github.com/YOUR_USERNAME/YOUR_REPO.git"   # SỬA LẠI

print("[START] Robot Vast.ai - Phiên bản ổn định")

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
git clone --depth 1 {GITHUB_REPO} /app || echo 'import time; [print("Running") for _ in range(999999)]' > /app/main.py
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --quiet
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
tail -f /dev/null
"""

while True:
    instances = get_instances()
    active = sum(1 for i in instances if str(i.get("status","")).lower() in {"running","loading","creating","starting"})

    print(f"[CHECK] Active: {active} | Total: {len(instances)}")

    if active >= MAX_INSTANCES:
        print("[OK] Đã có máy, nghỉ 10 phút")
        time.sleep(600)
        continue

    print("[🔍] Tìm máy 3090...")

    # Payload đơn giản hơn
    payload = {
        "rentable": True,
        "rented": False,
        "dph_total": {"lte": MAX_PRICE},
        "gpu_name": {"contains": "3090"},
        "limit": 5
    }

    try:
        r = requests.post(f"{BASE_URL}/bundles/", headers=HEADERS, json=payload, timeout=20)
        
        if r.status_code == 200:
            offers = r.json().get("offers", [])
            print(f"[DEBUG] Tìm thấy {len(offers)} offer")
            
            if offers:
                best = offers[0]
                print(f"[🎯] Thuê {best.get('gpu_name')} - ${best.get('dph_total')}")
                # Nếu bạn muốn tự động thuê thì uncomment đoạn dưới
                # rent_payload = {"image": "nvidia/cuda:11.7.1-runtime-ubuntu22.04", "disk": 40, "runtype": "ssh_direct", "onstart": create_onstart_script()}
                # requests.put(f"{BASE_URL}/asks/{best['id']}/", headers=HEADERS, json=rent_payload)
        else:
            print(f"[ERROR] API {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(60)
