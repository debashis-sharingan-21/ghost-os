"""Tests for pySerial connection manager and port enumeration."""

import pytest
from ghost_os.serial_link.serial_manager import SerialManager, SerialState, SerialPortInfo
from ghost_os.protocol.models import TelemetryFrame


def test_list_available_ports():
    ports = SerialManager.list_available_ports()
    assert isinstance(ports, list)
    for p in ports:
        assert isinstance(p, SerialPortInfo)
        d = p.to_dict()
        assert "port" in d
        assert "description" in d


def test_serial_manager_init_state():
    mgr = SerialManager()
    assert mgr.state == SerialState.DISCONNECTED
    assert mgr.is_connected is False
    assert mgr.port is None


def test_serial_manager_disconnect_safe():
    mgr = SerialManager()
    # Calling disconnect when already disconnected should not raise error
    mgr.disconnect()
    assert mgr.state == SerialState.DISCONNECTED


def test_serial_manager_non_blocking_connect():
    # Connecting to non-existent port should transition to RECONNECTING without raising unhandled exception
    mgr = SerialManager(reconnect_interval=0.1)
    ok = mgr.connect(port="COM999_NON_EXISTENT", baud=115200)
    assert ok is True
    # Clean disconnect
    mgr.disconnect()
    assert mgr.state == SerialState.DISCONNECTED
