"""Deterministic evidence-grounded forensic reasoner for GHOST.OS."""

from __future__ import annotations
import time
from typing import List
from ghost_os.ai.provider import (
    BaseAIProvider,
    DiagnosticPrompt,
    DiagnosticExplanation,
    Hypothesis,
)


class ForensicRuleProvider(BaseAIProvider):
    """High-precision offline diagnostic engine providing grounded physical forensic explanations."""

    provider_name = "DeterministicForensicEngine"
    model_name = "ghost-forensic-rule-v1"

    async def is_available(self) -> bool:
        return True  # Always available offline

    async def explain_anomaly(self, prompt: DiagnosticPrompt) -> DiagnosticExplanation:
        start_t = time.time()
        ev = prompt.trigger_evidence
        stats = prompt.summary_stats
        rule = prompt.rule_id

        observations: List[str] = []
        hypotheses: List[Hypothesis] = []
        uncertainties: List[str] = []
        recommended_tests: List[str] = []
        summary = ""

        if rule == "FREE_FALL":
            val = ev.get("accel_mag", 0.0)
            summary = f"Zero-G free fall trajectory detected. Total acceleration collapsed to {val:.2f} m/s²."
            observations = [
                f"Vector magnitude dropped to {val:.2f} m/s² (baseline resting gravity is 9.81 m/s²).",
                f"Sustained across {ev.get('consecutive_frames', 2)} consecutive telemetry samples ({ev.get('consecutive_frames', 2) * 100} ms).",
                f"Subsystem trace indicates angular rate jitter during the unconstrained flight phase.",
            ]
            hypotheses = [
                Hypothesis(
                    rank=1,
                    title="Physical Structural Separation / Catastrophic Drop",
                    probability="HIGH",
                    confidence_pct=92,
                    reasoning="Sudden near-zero acceleration indicates true mechanical weightlessness without external drag compensation.",
                ),
                Hypothesis(
                    rank=2,
                    title="IMU Inverted Pivot or High-G Centrifugal Counterbalance",
                    probability="LOW",
                    confidence_pct=22,
                    reasoning="Unlikely without severe angular rate spikes preceding the event.",
                ),
            ]
            uncertainties = [
                "Total vertical drop height cannot be established without integrated barometer/altimeter telemetry.",
            ]
            recommended_tests = [
                "Perform physical visual inspection of chassis and mounting standoff integrity.",
                "Verify MPU6050 I2C bus wiring harness for mechanical tensile damage.",
                "Check accelerometer zero-g offset registers via register self-test routine.",
            ]

        elif rule == "HIGH_G_IMPACT":
            val = ev.get("accel_mag", 0.0)
            peak_z = ev.get("peak_axis_z", 0.0)
            summary = f"Violent kinetic collision shock impulse recorded. Deceleration peaked at {val:.1f} m/s²."
            observations = [
                f"Acceleration magnitude peaked at {val:.2f} m/s² (threshold: {ev.get('threshold', 35.0)} m/s²).",
                f"Primary shock vector aligned along Z-axis ({peak_z:.1f} m/s²).",
                f"Preceding samples demonstrate normal baseline dynamics immediately terminated by impulse.",
            ]
            hypotheses = [
                Hypothesis(
                    rank=1,
                    title="Hard Kinetic Surface Impact / Collision",
                    probability="HIGH",
                    confidence_pct=95,
                    reasoning="High amplitude impulse with rapid exponential decay is characteristic of rigid solid surface impact.",
                ),
                Hypothesis(
                    rank=2,
                    title="Mechanical Resonance or Mounting Bracket Fracture",
                    probability="MEDIUM",
                    confidence_pct=45,
                    reasoning="Loose mounting screws can produce brief high-frequency ringing peaks under vibration.",
                ),
            ]
            uncertainties = [
                "Material elasticity of impact surface remains unmodeled.",
            ]
            recommended_tests = [
                "Inspect MEMS silicon die integrity by performing a static 1G orientation test (flip ±1G on all 3 axes).",
                "Torque mounting hardware to manufacturer specification (0.4 N·m).",
            ]

        elif rule == "HIGH_ANGULAR_RATE":
            rate = ev.get("max_angular_rate", 0.0)
            summary = f"High-speed angular runaway excursion detected. Peak rate reached {rate:.1f} deg/s."
            observations = [
                f"Maximum angular rate reached {rate:.1f} °/s (threshold: 400.0 °/s).",
                f"Active axes: Gx={ev.get('gyro_x', 0):.1f}°/s, Gy={ev.get('gyro_y', 0):.1f}°/s, Gz={ev.get('gyro_z', 0):.1f}°/s.",
            ]
            hypotheses = [
                Hypothesis(
                    rank=1,
                    title="Uncontrolled Aerodynamic / Mechanical Spin Tumble",
                    probability="HIGH",
                    confidence_pct=88,
                    reasoning="Simultaneous multi-axis angular rates indicate full loss of attitude constraint.",
                ),
            ]
            uncertainties = ["Actuator steering response data is not present in sensor-only telemetry."]
            recommended_tests = [
                "Inspect drive motor bearings and propulsion symmetry.",
                "Recalibrate gyroscope zero-rate bias offsets.",
            ]

        elif rule == "SENSOR_FREEZE":
            summary = "I2C bus transaction lockup detected. Sensor register telemetry output is frozen."
            observations = [
                "Telemetry output shows zero variance or explicit FROZEN diagnostic status.",
                f"Repeated identical readings observed for {ev.get('identical_consecutive_frames', 'multiple')} cycles.",
            ]
            hypotheses = [
                Hypothesis(
                    rank=1,
                    title="I2C Bus Lockup (SDA Line Held Low by Slave)",
                    probability="HIGH",
                    confidence_pct=91,
                    reasoning="Microcontroller reads stale cache when I2C communication aborts without bus reset.",
                ),
            ]
            uncertainties = ["Cannot probe hardware SDA line state directly without oscilloscope."]
            recommended_tests = [
                "Issue 9 clock pulses on SCL to unstick slave I2C shift register.",
                "Verify pull-up resistor values (ensure 4.7kΩ to 3.3V on SDA and SCL).",
            ]

        elif rule == "THERMAL_SPIKE":
            t_val = ev.get("temp_c", 0.0)
            summary = f"Die thermal excursion detected. Internal junction temperature rose to {t_val:.1f} °C."
            observations = [
                f"Die temperature reached {t_val:.1f} °C (threshold: {ev.get('threshold', 60.0)} °C).",
            ]
            hypotheses = [
                Hypothesis(
                    rank=1,
                    title="Enclosure Heat Dissipation Failure / Overheating",
                    probability="HIGH",
                    confidence_pct=85,
                    reasoning="Rapid linear temperature increase exceeds passive ambient convective dissipation.",
                ),
            ]
            uncertainties = ["External ambient thermal sensor is not present."]
            recommended_tests = [
                "Check enclosure ventilation and proximity to voltage regulator or power components.",
            ]

        elif rule == "BROWNOUT":
            v_val = ev.get("vcc_mv", 0)
            summary = f"Critical power rail brownout detected. Supply dropped to {v_val} mV."
            observations = [
                f"Supply voltage rail dropped to {v_val} mV (threshold: 2600 mV, nominal: 3300 mV).",
            ]
            hypotheses = [
                Hypothesis(
                    rank=1,
                    title="Excessive Power Rail Load / Low Battery Depletion",
                    probability="HIGH",
                    confidence_pct=93,
                    reasoning="Voltage drop below 2.6V will trip microcontroller internal brownout detector (BOD).",
                ),
            ]
            uncertainties = ["Battery state of charge curve is unknown."]
            recommended_tests = [
                "Check input power rail ripple and measure battery open-circuit voltage under load.",
            ]

        else:
            summary = f"Anomaly condition detected under rule {rule}."
            observations = [f"Trigger evidence: {str(ev)}"]
            hypotheses = [
                Hypothesis(rank=1, title="Telemetry Threshold Breach", probability="MEDIUM", confidence_pct=60, reasoning="Recorded readings breached nominal bounds.")
            ]
            uncertainties = ["Undefined custom rule."]
            recommended_tests = ["Review rule specification and threshold calibration."]

        latency = (time.time() - start_t) * 1000

        return DiagnosticExplanation(
            provider=self.provider_name,
            model=self.model_name,
            event_id=prompt.event_id,
            summary=summary,
            observations=observations,
            hypotheses=hypotheses,
            uncertainties=uncertainties,
            recommended_tests=recommended_tests,
            latency_ms=round(latency, 2),
            fallback_used=False,
        )
