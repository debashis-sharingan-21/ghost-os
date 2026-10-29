"""Deterministic anomaly detection rules for GHOST.OS."""

from __future__ import annotations
import math
from typing import Optional, List, Dict, Any
from ghost_os.protocol.models import TelemetryFrame


class AnomalyEvent:
    """Represents a detected anomaly event with evidence and lifecycle state."""

    def __init__(
        self,
        event_id: str,
        rule_id: str,
        title: str,
        severity: str,
        ts_onset_ms: int,
        seq_onset: int,
        evidence: Dict[str, Any],
        preceding_trace: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.event_id = event_id
        self.rule_id = rule_id
        self.title = title
        self.severity = severity  # "CRITICAL", "WARNING", "INFO"
        self.ts_onset_ms = ts_onset_ms
        self.ts_recovery_ms: Optional[int] = None
        self.seq_onset = seq_onset
        self.seq_recovery: Optional[int] = None
        self.is_active = True
        self.evidence = evidence
        self.preceding_trace = preceding_trace or []
        self.recovery_condition: str = "Pending nominal telemetry restoration"

    def mark_recovered(self, ts_recovery_ms: int, seq_recovery: int) -> None:
        self.is_active = False
        self.ts_recovery_ms = ts_recovery_ms
        self.seq_recovery = seq_recovery
        self.recovery_condition = "Telemetry parameters stabilized within nominal tolerances"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "rule_id": self.rule_id,
            "title": self.title,
            "severity": self.severity,
            "ts_onset_ms": self.ts_onset_ms,
            "ts_recovery_ms": self.ts_recovery_ms,
            "seq_onset": self.seq_onset,
            "seq_recovery": self.seq_recovery,
            "is_active": self.is_active,
            "evidence": self.evidence,
            "recovery_condition": self.recovery_condition,
            "trace_length": len(self.preceding_trace),
        }


class BaseAnomalyRule:
    """Base interface for all deterministic anomaly detection rules."""

    rule_id: str = "base_rule"
    title: str = "Base Rule"
    severity: str = "WARNING"

    def evaluate(self, frame: TelemetryFrame, window: List[TelemetryFrame]) -> Optional[Dict[str, Any]]:
        """Evaluates a frame against history window. Returns evidence dict if breached, else None."""
        raise NotImplementedError

    def is_cleared(self, frame: TelemetryFrame) -> bool:
        """Evaluates if the breach condition has cleared."""
        raise NotImplementedError


class FreeFallRule(BaseAnomalyRule):
    """Detects near zero-G free-fall drop condition persistent for >= 2 frames."""

    rule_id = "FREE_FALL"
    title = "Near Zero-G Free Fall Excursion"
    severity = "CRITICAL"

    def __init__(self, threshold_mag: float = 2.0, persistence_frames: int = 2) -> None:
        self.threshold = threshold_mag
        self.persistence = persistence_frames
        self.consecutive_count = 0

    def evaluate(self, frame: TelemetryFrame, window: List[TelemetryFrame]) -> Optional[Dict[str, Any]]:
        if frame.mpu6050.accel_mag < self.threshold:
            self.consecutive_count += 1
            if self.consecutive_count >= self.persistence:
                return {
                    "accel_mag": frame.mpu6050.accel_mag,
                    "threshold": self.threshold,
                    "consecutive_frames": self.consecutive_count,
                    "unit": "m/s²",
                }
        else:
            self.consecutive_count = 0
        return None

    def is_cleared(self, frame: TelemetryFrame) -> bool:
        # Cleared when normal gravity restored (between 7.5 and 12.5 m/s^2)
        return 7.5 <= frame.mpu6050.accel_mag <= 12.5


class HighGImpactRule(BaseAnomalyRule):
    """Detects severe kinetic collision / deceleration impulse (> 35.0 m/s^2)."""

    rule_id = "HIGH_G_IMPACT"
    title = "Severe Kinetic Collision / High-G Impact"
    severity = "CRITICAL"

    def __init__(self, threshold_mag: float = 35.0) -> None:
        self.threshold = threshold_mag

    def evaluate(self, frame: TelemetryFrame, window: List[TelemetryFrame]) -> Optional[Dict[str, Any]]:
        if frame.mpu6050.accel_mag >= self.threshold:
            return {
                "accel_mag": frame.mpu6050.accel_mag,
                "threshold": self.threshold,
                "peak_axis_z": frame.mpu6050.accel_z,
                "unit": "m/s²",
            }
        return None

    def is_cleared(self, frame: TelemetryFrame) -> bool:
        return frame.mpu6050.accel_mag < 15.0


class HighAngularRateRule(BaseAnomalyRule):
    """Detects uncontrolled angular tumble or spin exceeding 400 deg/s."""

    rule_id = "HIGH_ANGULAR_RATE"
    title = "Loss of Attitude Control (Tumble Spin)"
    severity = "WARNING"

    def __init__(self, threshold_rate: float = 400.0) -> None:
        self.threshold = threshold_rate

    def evaluate(self, frame: TelemetryFrame, window: List[TelemetryFrame]) -> Optional[Dict[str, Any]]:
        max_rate = max(
            abs(frame.mpu6050.gyro_x),
            abs(frame.mpu6050.gyro_y),
            abs(frame.mpu6050.gyro_z),
        )
        if max_rate >= self.threshold:
            return {
                "max_angular_rate": max_rate,
                "gyro_x": frame.mpu6050.gyro_x,
                "gyro_y": frame.mpu6050.gyro_y,
                "gyro_z": frame.mpu6050.gyro_z,
                "threshold": self.threshold,
                "unit": "deg/s",
            }
        return None

    def is_cleared(self, frame: TelemetryFrame) -> bool:
        max_rate = max(abs(frame.mpu6050.gyro_x), abs(frame.mpu6050.gyro_y), abs(frame.mpu6050.gyro_z))
        return max_rate < 100.0


class SensorFreezeRule(BaseAnomalyRule):
    """Detects frozen sensor flatline (zero variance or explicit FROZEN status)."""

    rule_id = "SENSOR_FREEZE"
    title = "I2C Sensor Register Lockup (Freeze)"
    severity = "CRITICAL"

    def __init__(self, identical_threshold: int = 6) -> None:
        self.identical_threshold = identical_threshold

    def evaluate(self, frame: TelemetryFrame, window: List[TelemetryFrame]) -> Optional[Dict[str, Any]]:
        if frame.mpu6050.status == "FROZEN":
            return {
                "status": "FROZEN",
                "accel_x": frame.mpu6050.accel_x,
                "accel_z": frame.mpu6050.accel_z,
                "reason": "Explicit FROZEN flag reported by hardware/sim",
            }

        if len(window) >= self.identical_threshold:
            recent = window[-self.identical_threshold:]
            # Check if all recent accel readings are bit-for-bit identical
            first = recent[0].mpu6050
            identical = all(
                f.mpu6050.accel_x == first.accel_x and
                f.mpu6050.accel_y == first.ay and
                f.mpu6050.accel_z == first.az and
                f.mpu6050.gyro_x == first.gx
                for f in recent
            )
            if identical:
                return {
                    "identical_consecutive_frames": len(recent),
                    "accel_x": first.accel_x,
                    "accel_z": first.accel_z,
                    "reason": "Zero variance detected across moving window",
                }
        return None

    def is_cleared(self, frame: TelemetryFrame) -> bool:
        return frame.mpu6050.status == "OK"


class SequenceDiscontinuityRule(BaseAnomalyRule):
    """Detects sequence gaps indicating lost UART packets."""

    rule_id = "SEQUENCE_GAP"
    title = "Telemetry Sequence Discontinuity / Drop"
    severity = "WARNING"

    def __init__(self, max_allowed_gap: int = 2) -> None:
        self.max_allowed_gap = max_allowed_gap
        self.last_seq: Optional[int] = None

    def evaluate(self, frame: TelemetryFrame, window: List[TelemetryFrame]) -> Optional[Dict[str, Any]]:
        if self.last_seq is not None:
            gap = frame.seq - (self.last_seq + 1)
            self.last_seq = frame.seq
            if gap >= self.max_allowed_gap:
                return {
                    "expected_seq": self.last_seq + 1,
                    "received_seq": frame.seq,
                    "dropped_packets": gap,
                }
        else:
            self.last_seq = frame.seq
        return None

    def is_cleared(self, frame: TelemetryFrame) -> bool:
        return True  # Transient gap clears immediately on next consecutive packet


class ThermalRunawayRule(BaseAnomalyRule):
    """Detects junction temperature exceeding safe threshold (> 60 C)."""

    rule_id = "THERMAL_SPIKE"
    title = "Internal Die Overheating"
    severity = "WARNING"

    def __init__(self, max_temp_c: float = 60.0) -> None:
        self.max_temp_c = max_temp_c

    def evaluate(self, frame: TelemetryFrame, window: List[TelemetryFrame]) -> Optional[Dict[str, Any]]:
        if frame.mpu6050.temp_c >= self.max_temp_c:
            return {
                "temp_c": frame.mpu6050.temp_c,
                "threshold": self.max_temp_c,
                "unit": "°C",
            }
        return None

    def is_cleared(self, frame: TelemetryFrame) -> bool:
        return frame.mpu6050.temp_c < 50.0


class BrownoutRule(BaseAnomalyRule):
    """Detects supply voltage rail dropping below critical 2.6V."""

    rule_id = "BROWNOUT"
    title = "Supply Rail Voltage Brownout"
    severity = "CRITICAL"

    def __init__(self, min_vcc_mv: int = 2600) -> None:
        self.min_vcc_mv = min_vcc_mv

    def evaluate(self, frame: TelemetryFrame, window: List[TelemetryFrame]) -> Optional[Dict[str, Any]]:
        if frame.health.vcc_mv < self.min_vcc_mv:
            return {
                "vcc_mv": frame.health.vcc_mv,
                "threshold": self.min_vcc_mv,
                "unit": "mV",
            }
        return None

    def is_cleared(self, frame: TelemetryFrame) -> bool:
        return frame.health.vcc_mv >= 3000
