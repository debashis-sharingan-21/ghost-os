import json
import os
import sys
import time
import urllib.request
import serial

PORT = "COM9"
BAUD = 115200
DURATION_SEC = 10

def verify_serial():
    print(f"[1/4] Opening {PORT} at {BAUD} baud to verify ESP32 boot and telemetry...", flush=True)
    lines = []
    start = time.time()
    try:
        with serial.Serial(PORT, BAUD, timeout=1.0) as ser:
            # Clear input buffer
            ser.reset_input_buffer()
            while time.time() - start < DURATION_SEC:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    lines.append(line)
                    print(f"  UART: {line}", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed reading serial port {PORT}: {e}", flush=True)
        return False, []

    print(f"\n[2/4] Serial port closed. Collected {len(lines)} lines.", flush=True)
    return True, lines

def connect_backend():
    print(f"\n[3/4] Connecting GHOST.OS backend to {PORT} ...", flush=True)
    url = "http://127.0.0.1:8000/api/serial/connect"
    payload = json.dumps({"port": PORT, "baud": BAUD}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"  Backend response: {data}", flush=True)
    except Exception as e:
        print(f"[ERROR] Backend connect failed: {e}", flush=True)
        return False

    time.sleep(2.0)
    # Check latest telemetry
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/telemetry/recent?limit=1", timeout=5) as resp:
            data = json.loads(resp.read().decode())
            latest_frame = data.get("frames", [{}])[-1] if data.get("frames") else {}
            print(f"  Latest Telemetry: {json.dumps(latest_frame, indent=2)}", flush=True)
            if latest_frame.get("simulated") is False:
                print("  CONFIRMED: simulated == False! Live hardware stream linked!", flush=True)
                return True
            else:
                print(f"  NOTE: simulated == {latest_frame.get('simulated')}", flush=True)
                return False
    except Exception as e:
        print(f"[ERROR] Failed checking latest telemetry: {e}", flush=True)
        return False

if __name__ == "__main__":
    ok, lines = verify_serial()
    if ok:
        connect_backend()
