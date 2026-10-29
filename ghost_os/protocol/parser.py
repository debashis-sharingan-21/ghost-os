"""Stream parser and deserializer for GHOST.OS JSON Lines protocol."""

from __future__ import annotations
import json
import logging
from typing import Optional, Tuple
from pydantic import ValidationError
from ghost_os.protocol.models import TelemetryFrame

logger = logging.getLogger("ghost_os.protocol")


class StreamParserStats:
    """Tracks parser telemetry health metrics."""
    def __init__(self) -> None:
        self.frames_parsed: int = 0
        self.bytes_processed: int = 0
        self.corrupt_lines: int = 0
        self.non_json_lines: int = 0
        self.seq_gaps: int = 0
        self.last_seq: Optional[int] = None

    def record_success(self, frame: TelemetryFrame, line_len: int) -> None:
        self.frames_parsed += 1
        self.bytes_processed += line_len
        if self.last_seq is not None:
            expected = self.last_seq + 1
            if frame.seq > expected:
                self.seq_gaps += (frame.seq - expected)
        self.last_seq = frame.seq

    def record_corrupt(self, line_len: int, is_non_json: bool = False) -> None:
        self.bytes_processed += line_len
        self.corrupt_lines += 1
        if is_non_json:
            self.non_json_lines += 1

    def to_dict(self) -> dict:
        return {
            "frames_parsed": self.frames_parsed,
            "bytes_processed": self.bytes_processed,
            "corrupt_lines": self.corrupt_lines,
            "non_json_lines": self.non_json_lines,
            "seq_gaps": self.seq_gaps,
            "last_seq": self.last_seq,
        }


class ProtocolParser:
    """Parses raw lines or bytes into validated TelemetryFrame objects."""

    def __init__(self) -> None:
        self.stats = StreamParserStats()

    def parse_line(self, line: str | bytes) -> Tuple[Optional[TelemetryFrame], Optional[str]]:
        """Parses a single line into a TelemetryFrame.
        
        Returns:
            (frame, None) on success.
            (None, error_message) on failure.
        """
        if isinstance(line, bytes):
            try:
                line_str = line.decode("utf-8", errors="replace").strip()
            except Exception as e:
                self.stats.record_corrupt(len(line))
                return None, f"Decode error: {e}"
        else:
            line_str = line.strip()

        if not line_str:
            return None, "Empty line"

        # Check if line looks like JSON (starts with '{' and ends with '}')
        if not (line_str.startswith("{") and line_str.endswith("}")):
            self.stats.record_corrupt(len(line_str), is_non_json=True)
            return None, f"Non-JSON line discarded: {line_str[:40]}..."

        try:
            data = json.loads(line_str)
        except json.JSONDecodeError as err:
            self.stats.record_corrupt(len(line_str), is_non_json=False)
            return None, f"JSON syntax error: {err.msg} at pos {err.pos}"

        try:
            frame = TelemetryFrame.model_validate(data)
            self.stats.record_success(frame, len(line_str))
            return frame, None
        except ValidationError as val_err:
            self.stats.record_corrupt(len(line_str), is_non_json=False)
            return None, f"Schema validation error: {val_err.errors()[0]['msg']}"
        except Exception as ex:
            self.stats.record_corrupt(len(line_str), is_non_json=False)
            return None, f"Unexpected validation error: {ex}"
