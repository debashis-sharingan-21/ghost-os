import asyncio
import json
import os
import subprocess
import time
import urllib.request
import base64
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = r"C:\Users\Omen\Downloads\ghost-os\docs\assets\proof-of-work"
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", "C:\\temp"), "chrome_cdp_profile_stages")

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def capture():
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--remote-debugging-port=9223",
        f"--user-data-dir={USER_DATA_DIR}",
        "--window-size=1920,1080",
        "--disable-extensions",
        "--enable-webgl",
        "--ignore-certificate-errors",
        "about:blank"
    ]
    proc = subprocess.Popen(cmd)
    try:
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:9223/json") as resp:
                    tabs = json.loads(resp.read().decode())
                    for t in tabs:
                        if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                            ws_url = t["webSocketDebuggerUrl"]
                            break
                    if ws_url:
                        break
            except Exception:
                pass
            time.sleep(0.5)

        if not ws_url:
            raise RuntimeError("Could not find page target in Chrome DevTools Protocol")

        print(f"Connected to Chrome page: {ws_url}", flush=True)

        async with websockets.connect(ws_url, max_size=25*1024*1024) as ws:
            req_id = 1
            async def send_cmd(method, params=None):
                nonlocal req_id
                cid = req_id
                req_id += 1
                msg = {"id": cid, "method": method, "params": params or {}}
                await ws.send(json.dumps(msg))
                while True:
                    res = json.loads(await ws.recv())
                    if res.get("id") == cid:
                        return res.get("result", {})

            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            
            # Navigate to GHOST.OS
            print("Navigating to http://127.0.0.1:8000/ ...", flush=True)
            await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/"})
            await asyncio.sleep(4.0)

            # Stage 1: Ghost Gate
            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            gate_path = os.path.join(OUTPUT_DIR, "01-ghost-gate.png")
            with open(gate_path, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Captured Stage 1: {gate_path} ({os.path.getsize(gate_path)} bytes)", flush=True)

            # Stage 2: Hardware Awakening
            print("Triggering Stage 2 Awaken...", flush=True)
            await send_cmd("Runtime.evaluate", {
                "expression": "document.getElementById('btn-awaken').click()"
            })
            await asyncio.sleep(3.5)

            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            hw_path = os.path.join(OUTPUT_DIR, "02-hardware-awakening.png")
            with open(hw_path, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Captured Stage 2: {hw_path} ({os.path.getsize(hw_path)} bytes)", flush=True)

            # Stage 3: Command Center
            print("Entering Stage 3 Command Center...", flush=True)
            await send_cmd("Runtime.evaluate", {
                "expression": "document.getElementById('btn-skip-awakening').click()"
            })
            await asyncio.sleep(3.5)

            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            cmd_path = os.path.join(OUTPUT_DIR, "03-command-center.png")
            with open(cmd_path, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Captured Stage 3: {cmd_path} ({os.path.getsize(cmd_path)} bytes)", flush=True)

            print("SUCCESS: All 3 genuine stage screenshots captured!", flush=True)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(capture())
