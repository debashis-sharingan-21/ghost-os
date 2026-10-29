"""REST API routes for GHOST.OS server."""

from __future__ import annotations
from typing import Dict, Any, List
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from ghost_os.simulator.scenarios import AnomalyScenario, SCENARIO_METADATA

router = APIRouter(prefix="/api")


class ScenarioTriggerRequest(BaseModel):
    scenario: AnomalyScenario = Field(..., description="Scenario identifier")
    duration_sec: float | None = Field(default=None, ge=0.5, le=60.0)


@router.get("/status")
async def get_system_status(request: Request) -> Dict[str, Any]:
    """Returns general system status, simulator state, and connected hardware info."""
    app_state = request.app.state
    sim = app_state.simulator
    return {
        "status": "ONLINE",
        "proto": "ghost.v1",
        "mode": "SIMULATION" if not app_state.is_hardware_connected else "HARDWARE_SERIAL",
        "is_hardware_connected": app_state.is_hardware_connected,
        "serial_port": app_state.serial_port,
        "active_scenario": sim.current_scenario.value,
        "scenario_metadata": SCENARIO_METADATA.get(sim.current_scenario, {}),
        "clients_connected": app_state.ws_manager.client_count,
        "buffered_frames": len(app_state.history_buffer),
        "sample_hz": sim.sample_hz,
    }


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
