"""Tests for session recording and Digital Afterlife replay."""

import tempfile
import pytest
from pathlib import Path
from ghost_os.protocol.models import TelemetryFrame, MPU6050Data
from ghost_os.storage.recorder import SessionRecorder
from ghost_os.storage.replay import SessionReplayer


def test_session_recorder_and_replayer_cycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = SessionRecorder(storage_dir=tmpdir)
        session_id = recorder.start_recording("test_session")
        assert recorder.is_recording is True

        # Write 5 frames
        for i in range(5):
            f = TelemetryFrame(seq=i, mpu6050=MPU6050Data(accel_z=9.8 + (i * 0.1)))
            recorder.record_frame(f)

        summary = recorder.stop_recording()
        assert recorder.is_recording is False
        assert summary["frames_recorded"] == 5

        # Check list
        sessions = recorder.list_saved_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_id

        # Test Replayer
        replayed_frames = []
        replayer = SessionReplayer(on_frame=lambda f: replayed_frames.append(f))
        loaded = replayer.load_session(sessions[0]["path"])
        assert loaded is True
        assert len(replayer.frames) == 5

        # Step through frames
        step1 = replayer.step()
        assert step1 is not None
        assert step1.seq == 0
        assert len(replayed_frames) == 1
        assert replayer.progress_pct == 20.0
