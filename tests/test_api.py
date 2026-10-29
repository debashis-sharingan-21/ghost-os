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
    # Trigger free fall
    trigger_resp = client.post(
        "/api/simulator/scenario",
        json={"scenario": "free_fall", "duration_sec": 3.5},
    )
    assert trigger_resp.status_code == 200
    assert trigger_resp.json()["ok"] is True

    # Check status
    status_resp = client.get("/api/status")
    assert status_resp.json()["active_scenario"] == "free_fall"

    # Reset
    reset_resp = client.post("/api/simulator/reset")
    assert reset_resp.status_code == 200

    status_resp2 = client.get("/api/status")
    assert status_resp2.json()["active_scenario"] == "normal"


def test_telemetry_recent(client):
    response = client.get("/api/telemetry/recent?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "frames" in data
    assert isinstance(data["frames"], list)


def test_websocket_telemetry_stream(client):
    with client.websocket_connect("/ws/telemetry") as ws:
        # Should receive a telemetry frame
        data = ws.receive_json()
        assert data["proto"] == "ghost.v1"
        assert "seq" in data
        assert "mpu6050" in data
        assert "accel_z" in data["mpu6050"]
        assert "health" in data
        assert data["simulated"] is True
