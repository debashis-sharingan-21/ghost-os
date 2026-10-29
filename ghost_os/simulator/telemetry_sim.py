"""Deterministic MPU6050 and ESP32 telemetry simulator."""

from __future__ import annotations
import math
import random
import time
from typing import Optional, Tuple
from ghost_os.protocol.models import (
    TelemetryFrame,
    MPU6050Data,
    HealthData,
    DiagnosticFlags,
)
from ghost_os.simulator.scenarios import AnomalyScenario, SCENARIO_METADATA


class TelemetrySimulator:
    """Generates deterministic, physically grounded MPU6050 and ESP32 telemetry."""

    def __init__(
        self,
        device_id: str = "ESP32-GHOST-SIM",
        sample_hz: float = 10.0,
        seed: Optional[int] = 42,
    ) -> None:
        self.device_id = device_id
        self.sample_hz = sample_hz
        self.dt = 1.0 / sample_hz
        self.rng = random.Random(seed) if seed is not None else random.Random()
        
        self.seq = 0
        self.start_time = time.time()
        self.current_scenario = AnomalyScenario.NORMAL
        self.scenario_start_time = self.start_time
        self.scenario_duration = 0.0
        
        # Physics state
        self.base_temp = 26.5
        self.base_vcc = 3295
        self.free_heap = 218400
        self.frozen_reading: Optional[MPU6050Data] = None

    def trigger_scenario(self, scenario: AnomalyScenario, duration_sec: Optional[float] = None) -> None:
        """Deterministically activates an anomaly scenario."""
        self.current_scenario = scenario
        self.scenario_start_time = time.time()
        if duration_sec is not None:
            self.scenario_duration = duration_sec
        else:
            self.scenario_duration = SCENARIO_METADATA[scenario]["duration_sec"]
        
        if scenario == AnomalyScenario.SENSOR_FREEZE:
            # Capture snapshot to freeze
            self.frozen_reading = MPU6050Data(
                accel_x=0.015,
                accel_y=-0.022,
                accel_z=9.789,
                accel_mag=9.789,
                gyro_x=0.08,
                gyro_y=-0.04,
                gyro_z=0.01,
                temp_c=26.8,
                status="FROZEN",
            )
        else:
            self.frozen_reading = None

    def reset_scenario(self) -> None:
        """Returns to normal baseline immediately."""
        self.current_scenario = AnomalyScenario.NORMAL
        self.scenario_duration = 0.0
        self.frozen_reading = None

    def generate_next_frame(self) -> TelemetryFrame:
        """Produces the next deterministic telemetry frame."""
        now = time.time()
        uptime_ms = int((now - self.start_time) * 1000)
        ts_ms = int(now * 1000)
        self.seq += 1

        # Check scenario timeout
        if self.current_scenario != AnomalyScenario.NORMAL and self.scenario_duration > 0:
            elapsed = now - self.scenario_start_time
            if elapsed >= self.scenario_duration:
                # Scenario finished, return to normal
                self.reset_scenario()

        # Generate physics based on active scenario
        mpu_data, health_data, flags = self._compute_state(now, uptime_ms)

        frame = TelemetryFrame(
            proto="ghost.v1",
            seq=self.seq,
            ts_ms=ts_ms,
            device_id=self.device_id,
            simulated=True,
            mpu6050=mpu_data,
            health=health_data,
            flags=flags,
        )
        return frame

    def _compute_state(self, now: float, uptime_ms: int) -> Tuple[MPU6050Data, HealthData, DiagnosticFlags]:
        t = now - self.start_time
        noise_ax = self.rng.gauss(0, 0.03)
        noise_ay = self.rng.gauss(0, 0.03)
        noise_az = self.rng.gauss(0, 0.03)
        noise_gx = self.rng.gauss(0, 0.08)
        noise_gy = self.rng.gauss(0, 0.08)
        noise_gz = self.rng.gauss(0, 0.08)

        # Baseline resting state
        ax = noise_ax
        ay = noise_ay
        az = 9.806 + noise_az
        gx = noise_gx
        gy = noise_gy
        gz = noise_gz
        temp_c = self.base_temp + 0.3 * math.sin(t * 0.05) + self.rng.gauss(0, 0.05)
        vcc_mv = self.base_vcc + int(self.rng.gauss(0, 4))
        status = "OK"
        anomaly_active = False
        error_code = 0

        # Scenario specific physics
        sc_elapsed = now - self.scenario_start_time

        if self.current_scenario == AnomalyScenario.FREE_FALL:
            anomaly_active = True
            if sc_elapsed < 0.9:
                # In free fall, near zero-G
                ax = self.rng.gauss(0, 0.08)
                ay = self.rng.gauss(0, 0.08)
                az = self.rng.gauss(0, 0.08)
                gx = self.rng.gauss(0, 1.2)
                gy = self.rng.gauss(0, 1.2)
                gz = self.rng.gauss(0, 1.2)
                status = "DEGRADED"
                error_code = 0x01  # Free-fall flag
            elif sc_elapsed < 1.3:
                # Sudden severe impact on landing
                decay = math.exp(-(sc_elapsed - 0.9) * 10)
                az = 9.806 + (48.0 * decay) + self.rng.gauss(0, 2.0)
                ax = (12.0 * decay) + self.rng.gauss(0, 1.0)
                ay = (-8.0 * decay) + self.rng.gauss(0, 1.0)
                status = "DEGRADED"
                error_code = 0x02  # Shock impact flag
            else:
                # Settling
                anomaly_active = False

        elif self.current_scenario == AnomalyScenario.HIGH_G_IMPACT:
            anomaly_active = True
            decay = math.exp(-sc_elapsed * 4.5)
            # 45G peak impact
            impulse = 45.0 * decay
            ax += impulse * 0.7 + self.rng.gauss(0, 1.5)
            ay += -impulse * 0.4 + self.rng.gauss(0, 1.0)
            az += impulse * 0.9 + self.rng.gauss(0, 2.0)
            gx += impulse * 8.0 * math.sin(sc_elapsed * 30)
            gy += impulse * 6.0 * math.cos(sc_elapsed * 30)
            status = "DEGRADED" if decay > 0.1 else "OK"
            error_code = 0x02

        elif self.current_scenario == AnomalyScenario.TUMBLE_SPIN:
            anomaly_active = True
            decay = max(0.0, 1.0 - (sc_elapsed / self.scenario_duration))
            rate = 650.0 * decay
            gx = rate * math.sin(sc_elapsed * 8.0) + noise_gx
            gy = rate * math.cos(sc_elapsed * 7.5) + noise_gy
            gz = (rate * 0.8) + noise_gz
            # Centripetal acceleration
            ax += (rate * 0.02) ** 2 * 0.05
            ay += (rate * 0.02) ** 2 * 0.05
            status = "DEGRADED"
            error_code = 0x04

        elif self.current_scenario == AnomalyScenario.SENSOR_FREEZE:
            anomaly_active = True
            if self.frozen_reading is not None:
                return (
                    self.frozen_reading,
                    HealthData(
                        uptime_ms=uptime_ms,
                        free_heap=self.free_heap,
                        vcc_mv=vcc_mv,
                        loop_hz=self.sample_hz,
                    ),
                    DiagnosticFlags(calibrated=True, anomaly_active=True, error_code=0x08),
                )

        elif self.current_scenario == AnomalyScenario.THERMAL_SPIKE:
            anomaly_active = True
            # Temperature climbs rapidly up to 72°C
            progress = min(1.0, sc_elapsed / 3.0)
            temp_c = self.base_temp + (46.0 * progress) + self.rng.gauss(0, 0.2)
            status = "DEGRADED" if temp_c > 60.0 else "OK"
            error_code = 0x10

        elif self.current_scenario == AnomalyScenario.BROWNOUT:
            anomaly_active = True
            # Supply drops to 2350 mV
            vcc_mv = max(2250, int(self.base_vcc - 950 * min(1.0, sc_elapsed / 1.5)))
            status = "FAIL" if vcc_mv < 2500 else "DEGRADED"
            error_code = 0x20

        # Memory jitter simulation
        heap_jitter = int(self.rng.gauss(0, 128))
        free_heap = max(50000, self.free_heap + heap_jitter)

        mpu = MPU6050Data(
            accel_x=round(ax, 3),
            accel_y=round(ay, 3),
            accel_z=round(az, 3),
            accel_mag=round(math.sqrt(ax**2 + ay**2 + az**2), 3),
            gyro_x=round(gx, 2),
            gyro_y=round(gy, 2),
            gyro_z=round(gz, 2),
            temp_c=round(temp_c, 2),
            status=status,
        )

        health = HealthData(
            uptime_ms=uptime_ms,
            free_heap=free_heap,
            vcc_mv=vcc_mv,
            loop_hz=self.sample_hz,
            wifi_rssi=-54 if not anomaly_active else -78,
        )

        flags = DiagnosticFlags(
            calibrated=True,
            anomaly_active=anomaly_active,
            error_code=error_code,
        )

        return mpu, health, flags
