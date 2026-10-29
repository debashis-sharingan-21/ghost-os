"""Telemetry data models for GHOST.OS (protocol ghost.v1)."""

from __future__ import annotations
import math
import time
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class MPU6050Data(BaseModel):
    """MPU6050 6-DOF IMU motion and temperature data."""
    accel_x: float = Field(default=0.0, description="X-axis acceleration in m/s^2")
    accel_y: float = Field(default=0.0, description="Y-axis acceleration in m/s^2")
    accel_z: float = Field(default=9.81, description="Z-axis acceleration in m/s^2")
    accel_mag: float = Field(default=9.81, description="Acceleration vector magnitude in m/s^2")
    gyro_x: float = Field(default=0.0, description="X-axis roll rate in deg/s")
    gyro_y: float = Field(default=0.0, description="Y-axis pitch rate in deg/s")
    gyro_z: float = Field(default=0.0, description="Z-axis yaw rate in deg/s")
    temp_c: float = Field(default=25.0, description="Die temperature in degrees Celsius")
    status: Literal["OK", "DEGRADED", "FAIL", "FROZEN"] = Field(default="OK")

    @model_validator(mode="after")
    def compute_accel_mag(self) -> MPU6050Data:
        # Recompute accel_mag if missing or 0 while components exist
        calculated = math.sqrt(self.accel_x**2 + self.accel_y**2 + self.accel_z**2)
        if abs(self.accel_mag - calculated) > 0.05:
            # Sync with actual components
            object.__setattr__(self, "accel_mag", round(calculated, 3))
        return self


class HealthData(BaseModel):
    """Device operating health and performance diagnostics."""
    uptime_ms: int = Field(default=0, ge=0)
    free_heap: int = Field(default=200000, ge=0)
    vcc_mv: int = Field(default=3300, ge=0)
    loop_hz: float = Field(default=10.0, ge=0.0)
    wifi_rssi: Optional[int] = Field(default=None)


class DiagnosticFlags(BaseModel):
    """Flags indicating calibration and device-side error indicators."""
    calibrated: bool = Field(default=True)
    anomaly_active: bool = Field(default=False)
    error_code: int = Field(default=0)


class TelemetryFrame(BaseModel):
    """Complete GHOST.OS telemetry frame (ghost.v1)."""
    proto: Literal["ghost.v1"] = Field(default="ghost.v1")
    seq: int = Field(default=0, ge=0)
    ts_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    device_id: str = Field(default="ESP32-GHOST-SIM")
    simulated: bool = Field(default=False)
    mpu6050: MPU6050Data = Field(default_factory=MPU6050Data)
    health: HealthData = Field(default_factory=HealthData)
    flags: DiagnosticFlags = Field(default_factory=DiagnosticFlags)

    def to_json_line(self) -> str:
        """Serialize frame to a single JSON line without trailing newline."""
        return self.model_dump_json()

    @field_validator("proto")
    @classmethod
    def validate_proto(cls, v: str) -> str:
        if v != "ghost.v1":
            raise ValueError(f"Unsupported protocol version: {v}. Expected 'ghost.v1'")
        return v
