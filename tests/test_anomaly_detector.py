"""Tests for deterministic anomaly detection rules, recovery, and Ghost Trace."""

import pytest
from ghost_os.protocol.models import TelemetryFrame, MPU6050Data, HealthData
from ghost_os.anomaly.detector import AnomalyDetector
from ghost_os.anomaly.rules import (
    FreeFallRule,
    HighGImpactRule,
    HighAngularRateRule,
    SensorFreezeRule,
    SequenceDiscontinuityRule,
    ThermalRunawayRule,
    BrownoutRule,
)
from ghost_os.anomaly.ghost_trace import GhostTraceBuffer


def test_free_fall_rule_detection_and_recovery():
    rule = FreeFallRule(threshold_mag=2.0, persistence_frames=2)
    f_normal = TelemetryFrame(mpu6050=MPU6050Data(accel_z=9.81))
    f_drop1 = TelemetryFrame(mpu6050=MPU6050Data(accel_x=0.1, accel_y=0.1, accel_z=0.2, accel_mag=0.3))
    f_drop2 = TelemetryFrame(mpu6050=MPU6050Data(accel_x=0.1, accel_y=0.1, accel_z=0.2, accel_mag=0.3))

    assert rule.evaluate(f_drop1, []) is None  # Frame 1: pending persistence
    ev = rule.evaluate(f_drop2, [])            # Frame 2: triggers breach
    assert ev is not None
    assert ev["accel_mag"] < 0.5

    # Recovery
    assert rule.is_cleared(f_normal) is True


def test_high_g_impact_rule():
    rule = HighGImpactRule(threshold_mag=35.0)
    f_normal = TelemetryFrame(mpu6050=MPU6050Data(accel_z=9.81))
    f_impact = TelemetryFrame(mpu6050=MPU6050Data(accel_x=10.0, accel_y=5.0, accel_z=40.0, accel_mag=41.5))

    assert rule.evaluate(f_normal, []) is None
    ev = rule.evaluate(f_impact, [])
    assert ev is not None
    assert ev["accel_mag"] == 41.5
    assert rule.is_cleared(f_normal) is True


def test_angular_rate_rule():
    rule = HighAngularRateRule(threshold_rate=400.0)
    f_tumble = TelemetryFrame(mpu6050=MPU6050Data(gyro_x=450.0, gyro_y=-12.0, gyro_z=5.0))
    ev = rule.evaluate(f_tumble, [])
    assert ev is not None
    assert ev["max_angular_rate"] == 450.0


def test_sensor_freeze_rule_explicit_and_flatline():
    rule = SensorFreezeRule(identical_threshold=3)
    f_frozen_flag = TelemetryFrame(mpu6050=MPU6050Data(status="FROZEN"))
    ev = rule.evaluate(f_frozen_flag, [])
    assert ev is not None
    assert ev["status"] == "FROZEN"


def test_thermal_runaway_rule():
    rule = ThermalRunawayRule(max_temp_c=60.0)
    f_hot = TelemetryFrame(mpu6050=MPU6050Data(temp_c=68.5))
    ev = rule.evaluate(f_hot, [])
    assert ev is not None
    assert ev["temp_c"] == 68.5


def test_brownout_rule():
    rule = BrownoutRule(min_vcc_mv=2600)
    f_brownout = TelemetryFrame(health=HealthData(vcc_mv=2350))
    ev = rule.evaluate(f_brownout, [])
    assert ev is not None
    assert ev["vcc_mv"] == 2350


def test_anomaly_detector_lifecycle():
    detector = AnomalyDetector()
    f1 = TelemetryFrame(seq=1, mpu6050=MPU6050Data(accel_z=9.81))
    f2 = TelemetryFrame(seq=2, mpu6050=MPU6050Data(accel_x=0.0, accel_y=0.0, accel_z=0.2, accel_mag=0.2))
    f3 = TelemetryFrame(seq=3, mpu6050=MPU6050Data(accel_x=0.0, accel_y=0.0, accel_z=0.2, accel_mag=0.2))
    f4 = TelemetryFrame(seq=4, mpu6050=MPU6050Data(accel_z=9.81))

    detector.process_frame(f1)
    detector.process_frame(f2)
    new_events = detector.process_frame(f3)

    assert len(new_events) == 1
    assert new_events[0].rule_id == "FREE_FALL"
    assert detector.has_active_anomalies is True

    # Recovery
    detector.process_frame(f4)
    assert detector.has_active_anomalies is False
    assert len(detector.resolved_events) == 1
    assert detector.resolved_events[0].is_active is False
    assert detector.resolved_events[0].seq_recovery == 4


def test_ghost_trace_buffer():
    buf = GhostTraceBuffer(capacity=10)
    for i in range(15):
        buf.append(TelemetryFrame(seq=i, mpu6050=MPU6050Data(accel_z=float(i))))

    preceding = buf.capture_preceding(count=5)
    assert len(preceding) == 5
    assert preceding[-1]["seq"] == 14

    stats = buf.compute_summary_stats(preceding)
    assert stats["samples"] == 5
    assert stats["accel_mag_min"] >= 10.0
