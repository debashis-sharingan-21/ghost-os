"""Serial connection manager for GHOST.OS hardware telemetry acquisition."""

from __future__ import annotations
import logging
import threading
import time
from enum import Enum
from typing import Callable, List, Optional
import serial
import serial.tools.list_ports

from ghost_os.protocol.models import TelemetryFrame
from ghost_os.protocol.parser import ProtocolParser

logger = logging.getLogger("ghost_os.serial")


class SerialState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class SerialPortInfo:
    def __init__(self, port: str, description: str, hwid: str) -> None:
        self.port = port
        self.description = description
        self.hwid = hwid

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "description": self.description,
            "hwid": self.hwid,
        }


class SerialManager:
    """Robust non-blocking pySerial telemetry receiver with automatic reconnect."""

    def __init__(
        self,
        on_frame: Optional[Callable[[TelemetryFrame], None]] = None,
        on_status: Optional[Callable[[SerialState, str], None]] = None,
        reconnect_interval: float = 2.0,
    ) -> None:
        self.on_frame = on_frame
        self.on_status = on_status
        self.reconnect_interval = reconnect_interval
        
        self.port: Optional[str] = None
        self.baud: int = 115200
        self.state: SerialState = SerialState.DISCONNECTED
        self.status_message: str = "Serial interface idle"
        
        self.parser = ProtocolParser()
        self._serial: Optional[serial.Serial] = None
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @staticmethod
    def list_available_ports() -> List[SerialPortInfo]:
        """Scans and lists currently attached hardware serial COM ports."""
        found = []
        try:
            for p in serial.tools.list_ports.comports():
                found.append(SerialPortInfo(p.device, p.description, p.hwid or ""))
        except Exception as e:
            logger.error(f"Error enumerating COM ports: {e}")
        return found

    def connect(self, port: str, baud: int = 115200) -> bool:
        """Initiates connection to the specified COM port."""
        with self._lock:
            self.disconnect()
            self.port = port
            self.baud = baud
            self._stop_event.clear()
            self._set_state(SerialState.CONNECTING, f"Connecting to {port} @ {baud} bps...")

            self._worker_thread = threading.Thread(
                target=self._run_loop,
                name="SerialReaderThread",
                daemon=True,
            )
            self._worker_thread.start()
            return True

    def disconnect(self) -> None:
        """Gracefully disconnects and stops background reader thread."""
        self._stop_event.set()
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

        if self._worker_thread and self._worker_thread.is_alive():
            if threading.current_thread() != self._worker_thread:
                self._worker_thread.join(timeout=1.5)
        self._worker_thread = None

        self._set_state(SerialState.DISCONNECTED, "Serial link disengaged")

    @property
    def is_connected(self) -> bool:
        return self.state == SerialState.CONNECTED and self._serial is not None and self._serial.is_open

    def _set_state(self, state: SerialState, msg: str) -> None:
        self.state = state
        self.status_message = msg
        logger.info(f"[SerialManager] {state.value}: {msg}")
        if self.on_status:
            try:
                self.on_status(state, msg)
            except Exception as e:
                logger.error(f"Error in on_status callback: {e}")

    def _open_port(self) -> bool:
        if not self.port:
            return False
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                timeout=0.5,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            self._set_state(SerialState.CONNECTED, f"Linked to {self.port} at {self.baud} baud")
            return True
        except serial.SerialException as err:
            self._set_state(SerialState.RECONNECTING, f"Port {self.port} unavailable: {err}")
            return False
        except Exception as ex:
            self._set_state(SerialState.ERROR, f"Unexpected error opening {self.port}: {ex}")
            return False

    def _run_loop(self) -> None:
        """Main serial worker thread loop."""
        while not self._stop_event.is_set():
            if not self.is_connected:
                if not self._open_port():
                    # Backoff before reconnect attempt
                    self._stop_event.wait(self.reconnect_interval)
                    continue

            # Read lines
            try:
                assert self._serial is not None
                raw_bytes = self._serial.readline()
                if not raw_bytes:
                    continue  # Timeout occurred, loop back

                frame, err = self.parser.parse_line(raw_bytes)
                if frame and self.on_frame:
                    try:
                        self.on_frame(frame)
                    except Exception as cb_err:
                        logger.error(f"Error in on_frame callback: {cb_err}")
                elif err and not err.startswith("Empty line"):
                    logger.debug(f"Serial stream parse note: {err}")

            except serial.SerialException as s_err:
                logger.warning(f"Serial I/O error on {self.port}: {s_err}")
                if self._serial:
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                    self._serial = None
                self._set_state(SerialState.RECONNECTING, f"Carrier lost: {s_err}. Reconnecting...")
                self._stop_event.wait(self.reconnect_interval)
            except Exception as unk_err:
                logger.error(f"Unexpected error in serial reader: {unk_err}")
                self._stop_event.wait(0.5)

        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
