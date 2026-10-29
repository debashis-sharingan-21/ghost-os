"""Timestamped telemetry session recorder for Digital Afterlife."""

from __future__ import annotations
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
from ghost_os.protocol.models import TelemetryFrame

logger = logging.getLogger("ghost_os.storage.recorder")


class SessionRecorder:
    """Records telemetry streams into timestamped JSON Lines session files."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path(__file__).resolve().parent.parent.parent / "data" / "sessions"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.is_recording = False
        self.current_file_path: Optional[Path] = None
        self._file_handle = None
        self.frames_recorded = 0
        self.session_id: Optional[str] = None
        self.start_time: Optional[float] = None

    def start_recording(self, session_name: Optional[str] = None) -> str:
        """Begins recording a new session."""
        self.stop_recording()
        now_str = time.strftime("%Y%m%d_%H%M%S")
        prefix = session_name or "ghost_session"
        self.session_id = f"{prefix}_{now_str}"
        self.current_file_path = self.storage_dir / f"{self.session_id}.jsonl"

        self._file_handle = open(self.current_file_path, "w", encoding="utf-8")
        self.is_recording = True
        self.frames_recorded = 0
        self.start_time = time.time()

        # Write session metadata header
        header = {
            "type": "SESSION_HEADER",
            "session_id": self.session_id,
            "proto": "ghost.v1",
            "start_epoch_ms": int(self.start_time * 1000),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._file_handle.write(json.dumps(header) + "\n")
        self._file_handle.flush()
        logger.info(f"Started recording telemetry session: {self.session_id}")
        return self.session_id

    def record_frame(self, frame: TelemetryFrame) -> None:
        """Appends a frame to the active session file."""
        if not self.is_recording or not self._file_handle:
            return
        try:
            line = frame.to_json_line()
            self._file_handle.write(line + "\n")
            self.frames_recorded += 1
            if self.frames_recorded % 20 == 0:
                self._file_handle.flush()
        except Exception as e:
            logger.error(f"Error writing telemetry frame to session: {e}")

    def stop_recording(self) -> Optional[dict]:
        """Stops active recording and returns summary metadata."""
        if not self.is_recording:
            return None
        self.is_recording = False
        summary = None
        if self._file_handle:
            try:
                # Write footer
                footer = {
                    "type": "SESSION_FOOTER",
                    "session_id": self.session_id,
                    "frames_recorded": self.frames_recorded,
                    "duration_sec": round(time.time() - (self.start_time or time.time()), 2),
                    "end_epoch_ms": int(time.time() * 1000),
                }
                self._file_handle.write(json.dumps(footer) + "\n")
                self._file_handle.flush()
                self._file_handle.close()
                summary = footer
            except Exception as e:
                logger.error(f"Error closing session recording file: {e}")
            finally:
                self._file_handle = None

        logger.info(f"Stopped session recording: {self.session_id} ({self.frames_recorded} frames)")
        return summary

    def list_saved_sessions(self) -> list[dict]:
        """Lists all existing session recordings on disk."""
        sessions = []
        for p in self.storage_dir.glob("*.jsonl"):
            try:
                size_bytes = p.stat().st_size
                mtime = p.stat().st_mtime
                sessions.append({
                    "session_id": p.stem,
                    "filename": p.name,
                    "path": str(p),
                    "size_bytes": size_bytes,
                    "modified_epoch": mtime,
                })
            except Exception:
                pass
        sessions.sort(key=lambda s: s["modified_epoch"], reverse=True)
        return sessions
