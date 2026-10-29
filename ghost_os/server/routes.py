"""REST API routes for GHOST.OS server."""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from ghost_os.simulator.scenarios import AnomalyScenario, SCENARIO_METADATA
from ghost_os.serial_link.serial_manager import SerialManager

router = APIRouter(prefix="/api")


# --- Schemas ---

class ScenarioTriggerRequest(BaseModel):
    scenario: AnomalyScenario = Field(..., description="Scenario identifier")
    duration_sec: Optional[float] = Field(default=None, ge=0.5, le=60.0)


class SerialConnectRequest(BaseModel):
    port: str = Field(..., description="Serial COM port, e.g. COM3 or /dev/ttyUSB0")
    baud: int = Field(default=115200, description="Baud rate (default: 115200)")


class RecordStartRequest(BaseModel):
    session_name: Optional[str] = Field(default=None, description="Optional custom session label")


class ReplayLoadRequest(BaseModel):
    session_id: str = Field(..., description="ID of recorded session to load")


class ReplaySpeedRequest(BaseModel):
    speed: float = Field(default=1.0, ge=0.1, le=10.0)


# --- System Status ---

@router.get("/status")
async def get_system_status(request: Request) -> Dict[str, Any]:
    """Returns general system status, simulator state, and connected hardware info."""
    app_state = request.app.state
    sim = app_state.simulator
    detector = app_state.anomaly_detector
    serial_mgr = app_state.serial_manager
    recorder = app_state.session_recorder
    replayer = app_state.session_replayer

    return {
        "status": "ONLINE",
        "proto": "ghost.v1",
        "mode": "SIMULATION" if not serial_mgr.is_connected else "HARDWARE_SERIAL",
        "is_hardware_connected": serial_mgr.is_connected,
        "serial_state": serial_mgr.state.value,
        "serial_port": serial_mgr.port,
        "serial_baud": serial_mgr.baud,
        "active_scenario": sim.current_scenario.value,
        "scenario_metadata": SCENARIO_METADATA.get(sim.current_scenario, {}),
        "active_anomalies_count": len(detector.active_events),
        "total_anomalies_detected": detector.total_anomalies_detected,
        "is_recording": recorder.is_recording,
        "active_recording_session": recorder.session_id,
        "is_replaying": replayer.is_playing,
        "replay_session": replayer.session_id,
        "clients_connected": app_state.ws_manager.client_count,
        "buffered_frames": len(app_state.history_buffer),
        "sample_hz": sim.sample_hz,
    }


# --- Serial Link Endpoints ---

@router.get("/serial/ports")
async def list_serial_ports() -> Dict[str, Any]:
    """Scans and returns available physical COM ports."""
    ports = SerialManager.list_available_ports()
    return {"ports": [p.to_dict() for p in ports]}


@router.post("/serial/connect")
async def connect_serial(req: SerialConnectRequest, request: Request) -> Dict[str, Any]:
    """Connects pySerial manager to a physical serial port."""
    serial_mgr = request.app.state.serial_manager
    ok = serial_mgr.connect(req.port, req.baud)
    return {
        "ok": ok,
        "port": req.port,
        "baud": req.baud,
        "state": serial_mgr.state.value,
        "message": f"Attempting connection to {req.port} at {req.baud} bps",
    }


@router.post("/serial/disconnect")
async def disconnect_serial(request: Request) -> Dict[str, Any]:
    """Disconnects physical serial link and reverts to simulator."""
    serial_mgr = request.app.state.serial_manager
    serial_mgr.disconnect()
    return {
        "ok": True,
        "state": serial_mgr.state.value,
        "message": "Serial link disengaged. Simulator active.",
    }


# --- Simulator Scenarios ---

@router.get("/simulator/scenarios")
async def list_scenarios() -> Dict[str, Any]:
    """Returns all available deterministic anomaly scenarios."""
    scenarios = []
    for sc, meta in SCENARIO_METADATA.items():
        scenarios.append({
            "id": sc.value,
            "title": meta["title"],
            "description": meta["description"],
            "default_duration_sec": meta["duration_sec"],
            "severity": meta["severity"],
        })
    return {"scenarios": scenarios}


@router.post("/simulator/scenario")
async def trigger_scenario(req: ScenarioTriggerRequest, request: Request) -> Dict[str, Any]:
    """Triggers an anomaly scenario deterministically on the simulator."""
    app_state = request.app.state
    sim = app_state.simulator
    sim.trigger_scenario(req.scenario, req.duration_sec)
    return {
        "ok": True,
        "scenario": req.scenario.value,
        "duration_sec": sim.scenario_duration,
        "message": f"Scenario {req.scenario.value} triggered successfully",
    }


@router.post("/simulator/reset")
async def reset_scenario(request: Request) -> Dict[str, Any]:
    """Resets simulator immediately back to normal baseline."""
    app_state = request.app.state
    app_state.simulator.reset_scenario()
    return {"ok": True, "message": "Simulator reset to normal baseline"}


# --- Telemetry & Ghost Trace Endpoints ---

@router.get("/telemetry/recent")
async def get_recent_telemetry(request: Request, limit: int = 100) -> Dict[str, Any]:
    """Returns the most recent N buffered telemetry frames."""
    app_state = request.app.state
    buf = list(app_state.history_buffer)
    limit = max(1, min(limit, len(buf)))
    recent = [frame.model_dump() for frame in buf[-limit:]]
    return {
        "count": len(recent),
        "frames": recent,
    }


@router.get("/anomalies")
async def get_anomalies(request: Request) -> Dict[str, Any]:
    """Returns list of active and recent resolved anomaly events."""
    detector = request.app.state.anomaly_detector
    events = detector.get_all_events()
    return {
        "total_detected": detector.total_anomalies_detected,
        "active_count": len(detector.active_events),
        "events": events,
    }


@router.get("/anomalies/{event_id}/trace")
async def get_anomaly_trace(event_id: str, request: Request) -> Dict[str, Any]:
    """Returns the preceding Ghost Trace forensic evidence window for an anomaly."""
    detector = request.app.state.anomaly_detector
    target_event = None
    for ev in detector.active_events.values():
        if ev.event_id == event_id:
            target_event = ev
            break
    if not target_event:
        for ev in detector.resolved_events:
            if ev.event_id == event_id:
                target_event = ev
                break

    if not target_event:
        raise HTTPException(status_code=404, detail=f"Anomaly event '{event_id}' not found")

    stats = detector.trace_buffer.compute_summary_stats(target_event.preceding_trace)
    return {
        "event_id": target_event.event_id,
        "title": target_event.title,
        "severity": target_event.severity,
        "evidence": target_event.evidence,
        "trace_summary_stats": stats,
        "preceding_trace": target_event.preceding_trace,
    }


# --- AI Interrogation Endpoints ---

@router.get("/ai/status")
async def get_ai_status(request: Request) -> Dict[str, Any]:
    """Returns current status of Ollama and fallback forensic engine."""
    interrogator = request.app.state.interrogator
    return await interrogator.get_active_provider_status()


@router.post("/ai/interrogate/{event_id}")
async def interrogate_event(event_id: str, request: Request) -> Dict[str, Any]:
    """Generates an evidence-grounded AI diagnostic explanation for an anomaly."""
    detector = request.app.state.anomaly_detector
    interrogator = request.app.state.interrogator

    target_event = None
    for ev in detector.active_events.values():
        if ev.event_id == event_id:
            target_event = ev
            break
    if not target_event:
        for ev in detector.resolved_events:
            if ev.event_id == event_id:
                target_event = ev
                break

    if not target_event:
        raise HTTPException(status_code=404, detail=f"Anomaly event '{event_id}' not found")

    stats = detector.trace_buffer.compute_summary_stats(target_event.preceding_trace)
    explanation = await interrogator.interrogate_event(target_event, stats)
    return explanation.model_dump()


# --- Digital Afterlife Session Recording & Replay ---

@router.get("/sessions")
async def list_sessions(request: Request) -> Dict[str, Any]:
    """Lists saved telemetry session files on disk."""
    recorder = request.app.state.session_recorder
    return {"sessions": recorder.list_saved_sessions()}


@router.post("/sessions/record/start")
async def start_recording(req: RecordStartRequest, request: Request) -> Dict[str, Any]:
    """Starts recording live telemetry to a timestamped session file."""
    recorder = request.app.state.session_recorder
    session_id = recorder.start_recording(req.session_name)
    return {"ok": True, "session_id": session_id, "message": f"Recording session {session_id} active"}


@router.post("/sessions/record/stop")
async def stop_recording(request: Request) -> Dict[str, Any]:
    """Stops the active session recording."""
    recorder = request.app.state.session_recorder
    summary = recorder.stop_recording()
    return {"ok": True, "summary": summary}


@router.post("/sessions/replay/load")
async def load_session_replay(req: ReplayLoadRequest, request: Request) -> Dict[str, Any]:
    """Loads a session file for replay."""
    app_state = request.app.state
    recorder = app_state.session_recorder
    replayer = app_state.session_replayer

    # Find file path
    target_path = None
    for s in recorder.list_saved_sessions():
        if s["session_id"] == req.session_id:
            target_path = s["path"]
            break

    if not target_path:
        raise HTTPException(status_code=404, detail=f"Session file '{req.session_id}' not found")

    ok = replayer.load_session(target_path)
    return {
        "ok": ok,
        "session_id": req.session_id,
        "frames_loaded": len(replayer.frames),
    }


@router.post("/sessions/replay/play")
async def play_session_replay(request: Request) -> Dict[str, Any]:
    """Starts or resumes session replay."""
    replayer = request.app.state.session_replayer
    replayer.play()
    return {"ok": True, "is_playing": replayer.is_playing}


@router.post("/sessions/replay/pause")
async def pause_session_replay(request: Request) -> Dict[str, Any]:
    """Pauses session replay."""
    replayer = request.app.state.session_replayer
    replayer.pause()
    return {"ok": True, "is_playing": replayer.is_playing}


@router.post("/sessions/replay/speed")
async def set_replay_speed(req: ReplaySpeedRequest, request: Request) -> Dict[str, Any]:
    """Sets session replay speed multiplier (e.g. 0.5x, 1.0x, 2.0x)."""
    replayer = request.app.state.session_replayer
    replayer.set_speed(req.speed)
    return {"ok": True, "speed": replayer.speed}
