"""FastAPI application entrypoint for GHOST.OS telemetry server."""

from __future__ import annotations
import asyncio
import collections
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ghost_os.protocol.models import TelemetryFrame
from ghost_os.simulator.telemetry_sim import TelemetrySimulator
from ghost_os.server.ws import ConnectionManager
from ghost_os.server.routes import router as api_router

logger = logging.getLogger("ghost_os.server")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def telemetry_broadcast_loop(app: FastAPI) -> None:
    """Continuous background loop streaming telemetry frames at target Hz."""
    sim: TelemetrySimulator = app.state.simulator
    ws_mgr: ConnectionManager = app.state.ws_manager
    history = app.state.history_buffer
    interval = 1.0 / sim.sample_hz

    while True:
        loop_start = asyncio.get_event_loop().time()
        try:
            # Generate next frame (from simulator or active serial source)
            frame: TelemetryFrame = sim.generate_next_frame()
            history.append(frame)

            # Broadcast to WebSocket clients if any are connected
            if ws_mgr.client_count > 0:
                await ws_mgr.broadcast_json(frame.model_dump())
        except Exception as e:
            logger.error(f"Error in telemetry broadcast loop: {e}", exc_info=True)

        elapsed = asyncio.get_event_loop().time() - loop_start
        delay = max(0.005, interval - elapsed)
        await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Initialization
    app.state.simulator = TelemetrySimulator(device_id="ESP32-GHOST-SIM", sample_hz=10.0)
    app.state.ws_manager = ConnectionManager()
    app.state.history_buffer = collections.deque(maxlen=500)
    app.state.is_hardware_connected = False
    app.state.serial_port = None

    # Start background telemetry generator
    task = asyncio.create_task(telemetry_broadcast_loop(app))
    yield
    # Teardown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    """Factory to create and configure the FastAPI application."""
    app = FastAPI(
        title="GHOST.OS",
        description="The Machine Remembers — Real-Time Telemetry & Diagnostic Interface",
        version="1.0.0",
        lifespan=lifespan,
    )

    # API routes
    app.include_router(api_router)

    # Static assets
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
                # Keepalive / incoming command receiver
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            ws_mgr.disconnect(websocket)
        except Exception as e:
            ws_mgr.disconnect(websocket)

    return app


app = create_app()
