"""Scenario definitions for deterministic GHOST.OS telemetry simulation."""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any


class AnomalyScenario(str, Enum):
    NORMAL = "normal"
    FREE_FALL = "free_fall"
    HIGH_G_IMPACT = "high_g_impact"
    TUMBLE_SPIN = "tumble_spin"
    SENSOR_FREEZE = "sensor_freeze"
    THERMAL_SPIKE = "thermal_spike"
    BROWNOUT = "brownout"


SCENARIO_METADATA: Dict[AnomalyScenario, Dict[str, Any]] = {
    AnomalyScenario.NORMAL: {
        "title": "Nominal Baseline",
        "description": "Stable desk resting state with gravity on Z (9.81 m/s²) and minor sensor noise.",
        "duration_sec": 0,  # Continuous
        "severity": "NOMINAL",
    },
    AnomalyScenario.FREE_FALL: {
        "title": "Zero-G Free Fall Drop",
        "description": "Simulates structural drop: acceleration drops near 0 m/s² for ~800ms, followed by impact landing shock.",
        "duration_sec": 4.0,
        "severity": "CRITICAL",
    },
    AnomalyScenario.HIGH_G_IMPACT: {
        "title": "High-G Kinetic Impact",
        "description": "Sudden violent collision spike exceeding 40 m/s² with high-frequency ringing decay.",
        "duration_sec": 3.0,
        "severity": "CRITICAL",
    },
    AnomalyScenario.TUMBLE_SPIN: {
        "title": "Angular Rate Runaway (Tumble)",
        "description": "Multi-axis angular velocity excursion exceeding 500 deg/s indicating loss of attitude control.",
        "duration_sec": 4.0,
        "severity": "WARNING",
    },
    AnomalyScenario.SENSOR_FREEZE: {
        "title": "I2C Bus Lockup (Sensor Freeze)",
        "description": "MPU6050 stops updating registers; static flatline values with zero variance and FROZEN status.",
        "duration_sec": 5.0,
        "severity": "CRITICAL",
    },
    AnomalyScenario.THERMAL_SPIKE: {
        "title": "Die Thermal Runaway",
        "description": "Rapid internal junction temperature rise exceeding 68°C, threatening silicon degradation.",
        "duration_sec": 6.0,
        "severity": "WARNING",
    },
    AnomalyScenario.BROWNOUT: {
        "title": "VCC Rail Brownout",
        "description": "Supply voltage drops to 2400 mV, triggering brownout flag and corrupted packet bursts.",
        "duration_sec": 4.0,
        "severity": "CRITICAL",
    },
}
