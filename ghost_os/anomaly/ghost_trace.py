"""Ghost Trace: Circular forensic telemetry recorder for anomaly reconstruction."""

from __future__ import annotations
import collections
from typing import List, Dict, Any, Optional
from ghost_os.protocol.models import TelemetryFrame


class GhostTraceBuffer:
    """Maintains a bounded circular buffer of recent telemetry for pre-fault forensics."""

    def __init__(self, capacity: int = 150) -> None:
        self.capacity = capacity
        self.buffer = collections.deque(maxlen=capacity)

    def append(self, frame: TelemetryFrame) -> None:
        self.buffer.append(frame)

    def capture_preceding(self, count: int = 30) -> List[Dict[str, Any]]:
        """Returns the last N frames prior to an event."""
        frames = list(self.buffer)
        slice_frames = frames[-count:] if len(frames) >= count else frames
        return [f.model_dump() for f in slice_frames]

    def capture_window(self, center_seq: int, before: int = 25, after: int = 25) -> List[Dict[str, Any]]:
        """Extracts a forensic window centered on a specific frame sequence."""
        frames = list(self.buffer)
        target_idx = None
        for i, f in enumerate(frames):
            if f.seq == center_seq:
                target_idx = i
                break

        if target_idx is None:
            # Fall back to latest
            return self.capture_preceding(before + after)

        start = max(0, target_idx - before)
        end = min(len(frames), target_idx + after + 1)
        return [f.model_dump() for f in frames[start:end]]

    def compute_summary_stats(self, trace_frames: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates min, max, mean, and peak-to-peak deltas across a trace window."""
        if not trace_frames:
            return {}

        accel_mags = [f["mpu6050"]["accel_mag"] for f in trace_frames]
        temps = [f["mpu6050"]["temp_c"] for f in trace_frames]
        vccs = [f["health"]["vcc_mv"] for f in trace_frames]

        max_gyros = [
            max(
                abs(f["mpu6050"]["gyro_x"]),
                abs(f["mpu6050"]["gyro_y"]),
                abs(f["mpu6050"]["gyro_z"]),
            )
            for f in trace_frames
        ]

        return {
            "samples": len(trace_frames),
            "accel_mag_min": min(accel_mags),
            "accel_mag_max": max(accel_mags),
            "accel_mag_avg": round(sum(accel_mags) / len(accel_mags), 2),
            "gyro_max_rate": max(max_gyros),
            "temp_min": min(temps),
            "temp_max": max(temps),
            "vcc_min": min(vccs),
            "vcc_max": max(vccs),
        }
