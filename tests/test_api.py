"""Automated integration tests for GHOST.OS FastAPI server and API endpoints."""

import pytest
from starlette.testclient import TestClient
from ghost_os.server.app import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "GHOST.OS" in response.text
    assert "access-terminal" in response.text
    assert "stage-ghost-gate" in response.text
    assert "stage-hardware-awakening" in response.text


def test_api_status(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["proto"] == "ghost.v1"
    assert data["mode"] == "SIMULATION"
    assert data["is_hardware_connected"] is False
    assert data["active_scenario"] == "normal"


def test_simulator_scenarios_list(client):
    response = client.get("/api/simulator/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    ids = [sc["id"] for sc in data["scenarios"]]
    assert "free_fall" in ids
    assert "high_g_impact" in ids
    assert "tumble_spin" in ids
    assert "sensor_freeze" in ids


def test_trigger_and_reset_scenario(client):
    trigger_resp = client.post(
        "/api/simulator/scenario",
        json={"scenario": "free_fall", "duration_sec": 3.5},
    )
    assert trigger_resp.status_code == 200
    assert trigger_resp.json()["ok"] is True

    status_resp = client.get("/api/status")
    assert status_resp.json()["active_scenario"] == "free_fall"

    reset_resp = client.post("/api/simulator/reset")
    assert reset_resp.status_code == 200

    status_resp2 = client.get("/api/status")
    assert status_resp2.json()["active_scenario"] == "normal"


def test_serial_endpoints(client):
    ports_resp = client.get("/api/serial/ports")
    assert ports_resp.status_code == 200
    assert "ports" in ports_resp.json()

    disconn_resp = client.post("/api/serial/disconnect")
    assert disconn_resp.status_code == 200
    assert disconn_resp.json()["ok"] is True


def test_anomalies_and_ai_interrogation_endpoints(client):
    # Trigger an anomaly to produce an event
    client.post("/api/simulator/scenario", json={"scenario": "high_g_impact", "duration_sec": 2.0})

    anom_resp = client.get("/api/anomalies")
    assert anom_resp.status_code == 200
    data = anom_resp.json()
    assert "events" in data

    ai_status = client.get("/api/ai/status")
    assert ai_status.status_code == 200
    assert "fallback_available" in ai_status.json()


def test_sessions_endpoints(client):
    sessions_resp = client.get("/api/sessions")
    assert sessions_resp.status_code == 200
    assert "sessions" in sessions_resp.json()

    # Start and stop recording
    start_resp = client.post("/api/sessions/record/start", json={"session_name": "test_api_rec"})
    assert start_resp.status_code == 200
    assert start_resp.json()["ok"] is True

    stop_resp = client.post("/api/sessions/record/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["ok"] is True


def test_websocket_telemetry_stream(client):
    with client.websocket_connect("/ws/telemetry") as ws:
        data = ws.receive_json()
        assert data["proto"] == "ghost.v1"
        assert "seq" in data
        assert "mpu6050" in data
        assert "health" in data
