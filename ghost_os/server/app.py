"""FastAPI application entrypoint for GHOST.OS telemetry server."""

from __future__ import annotations
import asyncio
import collections
import logging
import queue
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ghost_os.protocol.models import TelemetryFrame
from ghost_os.simulator.telemetry_sim import TelemetrySimulator
from ghost_os.serial_link.serial_manager import SerialManager
from ghost_os.anomaly.ghost_trace import GhostTraceBuffer
from ghost_os.anomaly.detector import AnomalyDetector
from ghost_os.storage.recorder import SessionRecorder
from ghost_os.storage.replay import SessionReplayer
from ghost_os.ai.interrogator import ForensicInterrogator
from ghost_os.server.ws import ConnectionManager
from ghost_os.server.routes import router as api_router

logger = logging.getLogger("ghost_os.server")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def telemetry_broadcast_loop(app: FastAPI) -> None:
    """Continuous background loop dispatching telemetry and anomaly forensics at 10 Hz."""
    sim: TelemetrySimulator = app.state.simulator
    serial_mgr: SerialManager = app.state.serial_manager
    detector: AnomalyDetector = app.state.anomaly_detector
    recorder: SessionRecorder = app.state.session_recorder
    replayer: SessionReplayer = app.state.session_replayer
    ws_mgr: ConnectionManager = app.state.ws_manager
    history = app.state.history_buffer
    incoming_queue: queue.Queue = app.state.incoming_serial_queue

    interval = 1.0 / sim.sample_hz

    while True:
        loop_start = asyncio.get_event_loop().time()
        try:
            frame: TelemetryFrame | None = None

            # Priority 1: Digital Afterlife replay if active
            # (handled asynchronously by replayer, which pushes to history & ws)
            if replayer.is_playing:
                # Wait for replay frames pushed via callback
                await asyncio.sleep(0.02)
                continue

            # Priority 2: Physical hardware serial if connected
            if serial_mgr.is_connected:
                try:
                    frame = incoming_queue.get_nowait()
                except queue.Empty:
                    frame = None

            # Priority 3: Deterministic Simulator fallback
            if frame is None and not serial_mgr.is_connected:
                frame = sim.generate_next_frame()

            if frame is not None:
                # Evaluate deterministic anomaly detection & Ghost Trace
                new_events = detector.process_frame(frame)
                if detector.has_active_anomalies:
                    frame.flags.anomaly_active = True

                # Record frame if session recording is active
                if recorder.is_recording:
                    recorder.record_frame(frame)

                history.append(frame)

                # Broadcast live telemetry frame and new events to WebSockets
                if ws_mgr.client_count > 0:
                    payload = frame.model_dump()
                    if new_events:
                        payload["new_anomalies"] = [e.to_dict() for e in new_events]
                    await ws_mgr.broadcast_json(payload)

        except Exception as e:
            logger.error(f"Error in telemetry broadcast loop: {e}", exc_info=True)

        elapsed = asyncio.get_event_loop().time() - loop_start
        delay = max(0.005, interval - elapsed)
        await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager initializing core subsystems."""
    # Subsystems initialization
    app.state.incoming_serial_queue = queue.Queue(maxsize=100)
    app.state.trace_buffer = GhostTraceBuffer(capacity=200)

    def on_serial_frame(f: TelemetryFrame):
        try:
            app.state.incoming_serial_queue.put_nowait(f)
        except queue.Full:
            pass

    app.state.serial_manager = SerialManager(on_frame=on_serial_frame)
    app.state.simulator = TelemetrySimulator(device_id="ESP32-GHOST-SIM", sample_hz=10.0)
    app.state.anomaly_detector = AnomalyDetector(trace_buffer=app.state.trace_buffer)
    app.state.session_recorder = SessionRecorder()

    def on_replay_frame(f: TelemetryFrame):
        app.state.history_buffer.append(f)
        app.state.anomaly_detector.process_frame(f)
        asyncio.create_task(app.state.ws_manager.broadcast_json(f.model_dump()))

    app.state.session_replayer = SessionReplayer(on_frame=on_replay_frame)
    app.state.interrogator = ForensicInterrogator()
    app.state.ws_manager = ConnectionManager()
    app.state.history_buffer = collections.deque(maxlen=500)

    # Start background telemetry broadcast worker
    task = asyncio.create_task(telemetry_broadcast_loop(app))
    yield
    # Graceful Teardown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    app.state.serial_manager.disconnect()
    app.state.session_recorder.stop_recording()
    app.state.session_replayer.stop()


def create_app() -> FastAPI:
    """Factory to create and configure the FastAPI application."""
    app = FastAPI(
        title="GHOST.OS",
        description="The Machine Remembers — Real-Time Telemetry & Diagnostic Interface",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(api_router)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"status": "GHOST.OS Core Running", "proto": "ghost.v1"}

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry_endpoint(websocket: WebSocket):
        ws_mgr: ConnectionManager = app.state.ws_manager
        await ws_mgr.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            ws_mgr.disconnect(websocket)
        except Exception:
            ws_mgr.disconnect(websocket)

    return app


app = create_app()
