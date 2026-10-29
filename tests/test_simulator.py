"""Tests for the deterministic GHOST.OS telemetry simulator."""

import pytest
from ghost_os.simulator.telemetry_sim import TelemetrySimulator
from ghost_os.simulator.scenarios import AnomalyScenario


def test_simulator_nominal_generation():
    sim = TelemetrySimulator(seed=123)
    frame = sim.generate_next_frame()
    assert frame.proto == "ghost.v1"
    assert frame.seq == 1
    assert frame.simulated is True
    assert frame.mpu6050.status == "OK"
    assert 9.5 < frame.mpu6050.accel_z < 10.1
    assert frame.mpu6050.accel_mag > 9.0


def test_simulator_free_fall_scenario():
    sim = TelemetrySimulator(seed=123)
    sim.trigger_scenario(AnomalyScenario.FREE_FALL, duration_sec=2.0)
    frame = sim.generate_next_frame()
    assert frame.flags.anomaly_active is True
    assert frame.mpu6050.status == "DEGRADED"
    # In initial drop, acceleration magnitude drops near zero
    assert frame.mpu6050.accel_mag < 2.0


def test_simulator_impact_scenario():
    sim = TelemetrySimulator(seed=123)
    sim.trigger_scenario(AnomalyScenario.HIGH_G_IMPACT, duration_sec=2.0)
    frame = sim.generate_next_frame()
    assert frame.flags.anomaly_active is True
    assert frame.mpu6050.accel_mag > 25.0


def test_simulator_sensor_freeze_scenario():
    sim = TelemetrySimulator(seed=123)
    sim.trigger_scenario(AnomalyScenario.SENSOR_FREEZE, duration_sec=2.0)
    f1 = sim.generate_next_frame()
    f2 = sim.generate_next_frame()
    assert f1.mpu6050.status == "FROZEN"
    assert f2.mpu6050.status == "FROZEN"
    assert f1.mpu6050.accel_x == f2.mpu6050.accel_x
    assert f1.mpu6050.gyro_z == f2.mpu6050.gyro_z


def test_simulator_thermal_scenario():
    sim = TelemetrySimulator(seed=123)
    sim.trigger_scenario(AnomalyScenario.THERMAL_SPIKE, duration_sec=2.0)
    # Advance time or generate multiple frames
    frame = sim.generate_next_frame()
    assert frame.flags.anomaly_active is True
