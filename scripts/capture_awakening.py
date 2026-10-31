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
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", "C:\\temp"), "chrome_cdp_awakening")

async def capture_awakening():
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--remote-debugging-port=9226",
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
                with urllib.request.urlopen("http://127.0.0.1:9226/json") as resp:
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
            await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/"})
            await asyncio.sleep(2.0)
            await send_cmd("Runtime.evaluate", {
                "expression": "sessionStorage.setItem('ghost_skip_intro', 'true'); location.reload();"
            })
            await asyncio.sleep(3.5)

            # Trigger High-G Impact / Free Fall Anomaly
            print("Triggering simulator anomaly for 3D Ghost Awakening visual capture...", flush=True)
            await send_cmd("Runtime.evaluate", {
                "expression": "window.triggerScenario('high_g_impact', 5);"
            })
            await asyncio.sleep(1.2)

            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            p6 = os.path.join(OUTPUT_DIR, "06-ghost-awakening.png")
            with open(p6, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Saved: {p6} ({os.path.getsize(p6)} bytes)", flush=True)
            print("Done!", flush=True)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(capture_awakening())
