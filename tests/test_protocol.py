"""Tests for GHOST.OS telemetry protocol models and parser."""

import json
import pytest
from ghost_os.protocol.models import TelemetryFrame, MPU6050Data, HealthData, DiagnosticFlags
from ghost_os.protocol.parser import ProtocolParser


def test_telemetry_frame_defaults():
    frame = TelemetryFrame()
    assert frame.proto == "ghost.v1"
    assert frame.seq == 0
    assert frame.mpu6050.accel_z == 9.81
    assert frame.mpu6050.status == "OK"
    assert frame.simulated is False


def test_telemetry_frame_json_line():
    frame = TelemetryFrame(seq=12, device_id="TEST-DEV", simulated=True)
    line = frame.to_json_line()
    assert "\n" not in line
    data = json.loads(line)
    assert data["proto"] == "ghost.v1"
    assert data["seq"] == 12
    assert data["device_id"] == "TEST-DEV"
    assert data["simulated"] is True


def test_protocol_parser_valid_line():
    parser = ProtocolParser()
    frame = TelemetryFrame(seq=100)
    line = frame.to_json_line()

    parsed, err = parser.parse_line(line)
    assert err is None
    assert parsed is not None
    assert parsed.seq == 100
    assert parser.stats.frames_parsed == 1
    assert parser.stats.corrupt_lines == 0


def test_protocol_parser_rejects_bootloader_logs():
    parser = ProtocolParser()
    boot_log = "rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)"
    parsed, err = parser.parse_line(boot_log)
    assert parsed is None
    assert "Non-JSON line" in err
    assert parser.stats.non_json_lines == 1
    assert parser.stats.corrupt_lines == 1


def test_protocol_parser_rejects_malformed_json():
    parser = ProtocolParser()
    corrupt_line = '{"proto": "ghost.v1", "seq": 10, "mpu6050": {corrupted...}'
    parsed, err = parser.parse_line(corrupt_line)
    assert parsed is None
    assert "JSON syntax error" in err
    assert parser.stats.corrupt_lines == 1


def test_protocol_parser_seq_gap_tracking():
    parser = ProtocolParser()
    f1 = TelemetryFrame(seq=1).to_json_line()
    f2 = TelemetryFrame(seq=5).to_json_line()  # Gap of 3 packets (2, 3, 4)

    p1, _ = parser.parse_line(f1)
    assert p1.seq == 1
    assert parser.stats.seq_gaps == 0

    p2, _ = parser.parse_line(f2)
    assert p2.seq == 5
    assert parser.stats.seq_gaps == 3
