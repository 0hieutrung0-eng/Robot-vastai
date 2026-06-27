import os
import requests
import time
import threading
from fastapi import FastAPI
import uvicorn

app = FastAPI()
SYSTEM_STATUS = "Robot đang khởi động..."

@app.get("/")
def read_root():
    return {"status": "active", "message": SYSTEM_STATUS, "time": time.strftime("%Y-%m-%d %H:%M:%S")}

def run_web_server():
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

threading.Thread(target=run_web_server, daemon=True).start()

# ========================== CONFIG ==========================
VAST_API_KEY = os.getenv("VAST_API_KEY", "").strip()
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()

MAX_PRICE = 0.25
MAX_INSTANCES = 1
GITHUB_REPO = "/0hieutrung0-eng/Robot-vastai.git"

BASE_URL = "https://console.vast.ai/api/v1"

def get_auth_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {VAST_API_KEY}"
    }

def print_and_log(msg):
    global SYSTEM_STATUS
    SYSTEM_STATUS = msg
    print(msg, flush=True)

if not VAST_API_KEY or not AGENT_TOKEN:
    print_and_log("[❌] Thiếu API key!")
    while True: time.sleep(3600)

# ========================== ONSTART ==========================
def create_onstart_script():
    AUTH_URL = f"https://{AGENT_TOKEN}@github.com{GITHUB_REPO}"
    return f"""#!/bin/bash
echo "=== OnStart Started $(date) ===" > /root/agent.log
set -e
apt-get update && apt-get install -y git python3-pip curl htop
git config --global credential.helper ''
git config --global --add safe.directory /app
rm -rf /app
if git clone --depth 1 {AUTH_URL} /app; then
    echo "→ Clone OK" >> /root/agent.log
else
    echo "→ Clone FAIL" >> /root/agent.log && exit 1
fi
cd /app
[ -f requirements.txt ] && pip install -r requirements.txt --no-cache-dir -q
export TOKEN="{AGENT_TOKEN}"
nohup python3 main.py > agent.log 2>&1 &
echo "→ Agent started" >> /root/agent.log
sleep infinity
"""

# ========================== SEARCH ENGINE ==========================
def search_offers():
    search_endpoints = [
        "/bundles/",
        "/offers/search/",
        "/instances/search/",
        "/search/offers/",
        "/offers/",
        "/instances/query/",
        "/query/",
        "/asks/search/",
        "/search/"
    ]
    
    query_json = {
        "verified": True,
        "rentable": True,
        "gpu_name": {"in": ["RTX 3090", "RTX 3090 Ti"]},
        "dph_total": {"lte": MAX_PRICE},
        "type": "on-demand",
        "limit": 10
    }
    
    query_str = "verified=true rentable=true gpu_name~RTX_3090 dph_total<=0.25 limit=10"
    
    for ep in search_endpoints:
        url = BASE_URL + ep
        print_and_log(f"[TRY] {ep}")
        
        # Thử POST JSON
        try:
            r = requests.post(url, headers=get_auth_headers(), json=query_json, timeout=15)
            print_and_log(f"   → POST JSON: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                offers = data.get("offers") or data.get("instances") or data.get("results") or []
                if offers:
                    print_and_log(f"[✅] THÀNH CÔNG! Tìm thấy {len(offers)} máy.")
                    return offers
        except:
            pass
        
        # Thử GET với query string
        try:
            r = requests.get(url, headers=get_auth_headers(), params={"q": query_str}, timeout=15)
            print_and_log(f"   → GET query: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                offers = data.get("offers") or data.get("instances") or []
                if offers:
                    print_and_log(f"[✅] THÀNH CÔNG! Tìm thấy {len(offers)} máy.")
                    return offers
        except:
            pass
    
    print_and_log("[❌] Không tìm thấy endpoint search nào hoạt động.")
    return []

# ========================== MAIN ==========================
print_and_log("[🚀] Robot Vast.ai v2.7 - Exhaustive Search")

while True:
    instances = get_my_instances() if 'get_my_instances' in globals() else []
    active_count = sum(1 for inst in instances if inst.get("status") in ["running", "loading", "creating", "starting"])
    print_and_log(f"[CHECK] Đang hoạt động: {active_count}/{MAX_INSTANCES}")

    # Cleanup
    for inst in instances:
        if str(inst.get("status", "")).lower() in ["error", "dead", "stopped", "failed"]:
            requests.delete(f"{BASE_URL}/instances/{inst.get('id')}/", headers=get_auth_headers())

    if active_count >= MAX_INSTANCES:
        time.sleep(480)
        continue

    offers = search_offers()
    if not offers:
        time.sleep(45)
        continue

    offers.sort(key=lambda x: float(x.get("dph_total", 999)))
    best = offers[0]
    print_and_log(f"[🎯] Chọn máy: {best.get('gpu_name')} - ${best.get('dph_total')}/h")

    # Rent
    rent_payload = {
        "image": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
        "disk": 50,
        "onstart": create_onstart_script(),
        "runtype": "ssh_direct",
        "ssh": True,
        "direct": True
    }

    rent_resp = requests.put(
        f"{BASE_URL}/asks/{best['id']}/",
        headers=get_auth_headers(),
        json=rent_payload,
        timeout=60
    )

    if rent_resp.status_code in (200, 201):
        print_and_log("[🎉] THUÊ THÀNH CÔNG!")
        time.sleep(900)
    else:
        print_and_log(f"[❌] Thuê lỗi {rent_resp.status_code}")
        time.sleep(30)
