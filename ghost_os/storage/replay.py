"""Digital Afterlife: Session replay player for recorded telemetry."""

from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional, Callable
from ghost_os.protocol.models import TelemetryFrame
from ghost_os.protocol.parser import ProtocolParser

logger = logging.getLogger("ghost_os.storage.replay")


class SessionReplayer:
    """Replays saved telemetry sessions with speed and pause controls."""

    def __init__(self, on_frame: Optional[Callable[[TelemetryFrame], None]] = None) -> None:
        self.on_frame = on_frame
        self.frames: List[TelemetryFrame] = []
        self.session_id: Optional[str] = None
        self.current_index: int = 0
        self.is_playing: bool = False
        self.speed: float = 1.0  # 0.5x, 1.0x, 2.0x, 4.0x
        self._playback_task: Optional[asyncio.Task] = None
        self.parser = ProtocolParser()

    def load_session(self, file_path: str | Path) -> bool:
        """Loads and parses a session file into memory."""
        self.stop()
        p = Path(file_path)
        if not p.exists():
            logger.error(f"Replay file not found: {p}")
            return False

        loaded_frames = []
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if "SESSION_HEADER" in line or "SESSION_FOOTER" in line:
                        continue
                    frame, err = self.parser.parse_line(line)
                    if frame:
                        loaded_frames.append(frame)

            self.frames = loaded_frames
            self.session_id = p.stem
            self.current_index = 0
            logger.info(f"Loaded {len(self.frames)} frames from replay session: {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to load replay file {p}: {e}")
            return False

    def play(self) -> None:
        if not self.frames:
            return
        self.is_playing = True
        if self._playback_task is None or self._playback_task.done():
            self._playback_task = asyncio.create_task(self._replay_loop())

    def pause(self) -> None:
        self.is_playing = False

    def stop(self) -> None:
        self.is_playing = False
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
        self._playback_task = None
        self.current_index = 0

    def step(self) -> Optional[TelemetryFrame]:
        """Steps forward one frame."""
        if not self.frames or self.current_index >= len(self.frames):
            return None
        frame = self.frames[self.current_index]
        self.current_index += 1
        if self.on_frame:
            self.on_frame(frame)
        return frame

    def set_speed(self, speed: float) -> None:
        self.speed = max(0.1, min(10.0, speed))

    @property
    def progress_pct(self) -> float:
        if not self.frames:
            return 0.0
        return round((self.current_index / len(self.frames)) * 100, 1)

    async def _replay_loop(self) -> None:
        """Asynchronous playback pacing loop."""
        while self.is_playing and self.current_index < len(self.frames):
            curr_frame = self.frames[self.current_index]
            self.current_index += 1

            if self.on_frame:
                try:
                    self.on_frame(curr_frame)
                except Exception as err:
                    logger.error(f"Error in replay on_frame: {err}")

            if self.current_index < len(self.frames):
                next_frame = self.frames[self.current_index]
                delta_ms = next_frame.ts_ms - curr_frame.ts_ms
                if delta_ms <= 0 or delta_ms > 2000:
                    delta_ms = 100  # Default nominal 10Hz tick
                delay_sec = (delta_ms / 1000.0) / self.speed
                await asyncio.sleep(max(0.01, delay_sec))
            else:
                self.is_playing = False
                logger.info(f"Session replay {self.session_id} complete.")
                break
