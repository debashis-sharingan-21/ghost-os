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
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", "C:\\temp"), "chrome_cdp_suite2")

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def capture_all():
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--remote-debugging-port=9225",
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
                with urllib.request.urlopen("http://127.0.0.1:9225/json") as resp:
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

        print(f"Connected to Chrome CDP: {ws_url}", flush=True)

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
                        if "error" in res:
                            print(f"[CDP Error] {method}: {res['error']}", flush=True)
                        return res.get("result", {})

            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")

            # ----------------------------------------------------
            # 1. 04-architecture.png
            # ----------------------------------------------------
            print("Capturing 04-architecture.png ...", flush=True)
            await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/static/architecture_diagram.html"})
            await asyncio.sleep(2.0)
            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            p4 = os.path.join(OUTPUT_DIR, "04-architecture.png")
            with open(p4, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Saved: {p4} ({os.path.getsize(p4)} bytes)", flush=True)

            # ----------------------------------------------------
            # 2. Boot directly into Command Center via sessionStorage
            # ----------------------------------------------------
            print("Navigating to GHOST.OS with skip_intro ...", flush=True)
            await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/"})
            await asyncio.sleep(2.0)
            await send_cmd("Runtime.evaluate", {
                "expression": "sessionStorage.setItem('ghost_skip_intro', 'true'); location.reload();"
            })
            await asyncio.sleep(3.5)

            # Verify we are in Command Center
            check = await send_cmd("Runtime.evaluate", {
                "expression": "document.getElementById('stage-command-center').style.display"
            })
            print(f"Command Center display: {check.get('result', {}).get('value')}", flush=True)

            # ----------------------------------------------------
            # 3. Inject Simulator Anomaly (Free Fall Drop)
            # ----------------------------------------------------
            print("Injecting Simulator Scenario: free_fall ...", flush=True)
            await send_cmd("Runtime.evaluate", {
                "expression": "window.triggerScenario('free_fall', 4);"
            })
            await asyncio.sleep(4.0)

            # ----------------------------------------------------
            # 4. 05-ghost-trace.png
            # ----------------------------------------------------
            print("Switching to Ghost Trace Tab ...", flush=True)
            await send_cmd("Runtime.evaluate", {
                "expression": "window.switchTab('tab-trace');"
            })
            await asyncio.sleep(2.0)

            # Select first event card
            await send_cmd("Runtime.evaluate", {
                "expression": """
                (function() {
                    const cards = document.querySelectorAll('.event-card');
                    if (cards.length > 0) {
                        cards[0].click();
                        return 'Selected event: ' + cards[0].textContent.trim();
                    }
                    return 'No event cards';
                })();
                """
            })
            await asyncio.sleep(2.0)

            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            p5 = os.path.join(OUTPUT_DIR, "05-ghost-trace.png")
            with open(p5, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Saved: {p5} ({os.path.getsize(p5)} bytes)", flush=True)

            # ----------------------------------------------------
            # 5. 07-forensic-report.png
            # ----------------------------------------------------
            print("Interrogating event via Forensic AI ...", flush=True)
            await send_cmd("Runtime.evaluate", {
                "expression": "window.interrogateSelectedEvent();"
            })
            await asyncio.sleep(4.0)

            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            p7 = os.path.join(OUTPUT_DIR, "07-forensic-report.png")
            with open(p7, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Saved: {p7} ({os.path.getsize(p7)} bytes)", flush=True)

            # ----------------------------------------------------
            # 6. 08-digital-afterlife.png
            # ----------------------------------------------------
            print("Switching to Digital Afterlife Tab ...", flush=True)
            await send_cmd("Runtime.evaluate", {
                "expression": "window.switchTab('tab-replay');"
            })
            await asyncio.sleep(2.0)

            # Select session and load
            await send_cmd("Runtime.evaluate", {
                "expression": """
                (function() {
                    const sel = document.getElementById('replay-session-select');
                    if (sel && sel.options.length > 1) {
                        sel.selectedIndex = 1;
                        window.loadReplaySession();
                        return 'Loaded session: ' + sel.value;
                    }
                    return 'No replay options';
                })();
                """
            })
            await asyncio.sleep(2.5)

            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            p8 = os.path.join(OUTPUT_DIR, "08-digital-afterlife.png")
            with open(p8, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Saved: {p8} ({os.path.getsize(p8)} bytes)", flush=True)

            # ----------------------------------------------------
            # 7. 06-ghost-awakening.png (Reaction in Ghost Gate)
            # ----------------------------------------------------
            print("Reloading to Ghost Gate for 3D Skull Anomaly Reaction ...", flush=True)
            await send_cmd("Runtime.evaluate", {
                "expression": "sessionStorage.removeItem('ghost_skip_intro'); location.reload();"
            })
            await asyncio.sleep(3.5)

            # Trigger anomaly burst on Ghost Gate skull
            await send_cmd("Runtime.evaluate", {
                "expression": """
                (function() {
                    if (window.gate3D) {
                        window.gate3D.triggerAnomalyBurst('FREE_FALL', 'CRITICAL', 'FREE FALL DROP', 'SIMULATOR ANOMALY DEMONSTRATION');
                        return 'Triggered gate3D anomaly burst';
                    }
                    return 'gate3D not available';
                })();
                """
            })
            await asyncio.sleep(1.2)

            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            p6 = os.path.join(OUTPUT_DIR, "06-ghost-awakening.png")
            with open(p6, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            print(f"Saved: {p6} ({os.path.getsize(p6)} bytes)", flush=True)

            print("ALL ASSETS CAPTURED SUCCESSFULLY!", flush=True)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(capture_all())
