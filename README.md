# GHOST.OS — The Machine Remembers
### Real-Time ESP32 Telemetry, Deterministic Anomaly Detection & Forensic AI

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python: 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20WebSockets-009688.svg)](https://fastapi.tiangolo.com/)
[![Three.js](https://img.shields.io/badge/3D-Three.js%20(Offline%20Bundled)-black.svg)](https://threejs.org/)
[![Hardware](https://img.shields.io/badge/Target-ESP32--WROOM--32%20%2B%20MPU6050-red.svg)](https://www.espressif.com/)
[![Protocol](https://img.shields.io/badge/Protocol-ghost.v1%20JSONL-orange.svg)](docs/PROTOCOL.md)
[![Tests: 34 Passed](https://img.shields.io/badge/Tests-34%20Passing-brightgreen.svg)](tests/)

**GHOST.OS** is a high-reliability industrial SCADA instrumentation and telemetry platform engineered for embedded systems. Built around an **ESP32-WROOM-32** dual-core microcontroller and an **MPU6050 6-DOF IMU**, GHOST.OS features a versioned newline-delimited JSON (`ghost.v1`) streaming protocol, a deterministic physics simulator with 7 repeatable anomaly scenarios, sliding-window rule-based fault detection, **Ghost Trace** pre-fault evidence reconstruction, **Digital Afterlife** diagnostic session replay, and an evidence-grounded **Local AI Forensic Interrogator** (supporting local Ollama models with an autonomous deterministic offline fallback).

---

## Architecture & Visual Overview

![GHOST.OS Command Center](docs/assets/screenshots/command_center.png)

```
                        ┌─────────────────────────────────────────────────────────┐
                        │                   PHYSICAL HARDWARE                     │
                        │   ESP32-WROOM-32  <──[ I²C 400kHz ]──>  MPU6050 6-DOF   │
                        └───────────────────────────┬─────────────────────────────┘
                                                    │ USB UART (115200 8-N-1)
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           GHOST.OS PYTHON CORE RUNTIME                          │
│                                                                                 │
│   ┌─────────────────────┐      ┌────────────────────┐      ┌────────────────┐   │
│   │   pySerial Manager  │ ───> │  Protocol Parser   │ ───> │ Anomaly Engine │   │
│   │   (Auto-Reconnect)  │      │  (ghost.v1 JSONL)  │      │ (7 Rule Detect)│   │
│   └─────────────────────┘      └────────────────────┘      └───────┬────────┘   │
│              ▲                                                     │            │
│   ┌──────────┴──────────┐      ┌────────────────────┐              ▼            │
│   │ Telemetry Simulator │      │  Session Recorder  │      ┌────────────────┐   │
│   │ (7 Anomaly Scenarios│      │  & Replay Engine   │      │  Ghost Trace   │   │
│   └─────────────────────┘      └────────────────────┘      │ (Ring Buffer)  │   │
│                                                                    │            │
│                                ┌────────────────────┐              ▼            │
│                                │   AI Interrogator  │ <──── Diagnostic Evidence │
│                                │ (Ollama / Fallback)│                           │
│                                └────────────────────┘                           │
└───────────────────────────────────────────┬─────────────────────────────────────┘
                                            │ WebSocket Streaming (10 Hz)
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     THREE-STAGE RETRO CRT USER INTERFACE                        │
│                                                                                 │
│   [STAGE 1: GHOST GATE]    ──>   [STAGE 2: HARDWARE AWAKEN]  ──> [STAGE 3: SCADA]│
│   Procedural 3D WebGL Skull      3D ESP32 + MPU6050 PCB Trace    Live Signals   │
│   Living Eye Lights & Scan       I²C Energy Pulse Interconnect   Forensic Trace │
│   Interactive Mouse Parallax     Real-Time Boot Hardware Audit   AI Diagnostic  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3D Cinematic Interface

![GHOST.OS 3D Gate](docs/assets/screenshots/ghost_gate.png)

1. **GHOST GATE**: Full-screen CRT terminal with a procedural 3D WebGL skull, breathing neon wireframe contours, living point-light eye pupils that blink and observe cursor movements, and a signal sweep beam.
2. **HARDWARE AWAKENING**: Real 3D technical scene featuring an ESP32-WROOM-32 board, MPU6050 sensor, and dynamic traveling electrical pulses along the SDA and SCL I2C lines. Includes a real-time boot log auditing host hardware ports.
3. **COMMAND CENTER**: High-performance dual oscilloscopes with dynamic auto-scaling and in-canvas HUD readouts, Device Link controls, Anomaly Matrix, Ghost Trace timeline, AI Interrogation viewer, and CRT log console.

---

## Core Subsystems

### 1. Versioned JSON Lines Telemetry Protocol (`ghost.v1`)
High-resilience streaming format parsed and validated with Pydantic:
* **Motion Subsystem**: 3-axis acceleration ($A_x, A_y, A_z$), calculated vector magnitude ($|A|$), 3-axis angular rate ($G_x, G_y, G_z$), die temperature ($T^\circ\text{C}$), operational state (`OK`, `DEGRADED`, `FAIL`, `FROZEN`).
* **Health Subsystem**: Microcontroller uptime, FreeRTOS free heap (bytes), supply voltage ($V_{cc}$ mV), and actual telemetry loop frequency (Hz).
* **Diagnostic Flags**: Sensor calibration status, anomaly alert flag, and hardware error bitfield.
* **Stream Resilience**: Bootloader logs (`rst:0x1...`) and serial noise are stripped cleanly; sequence gaps are tracked and reported.

### 2. Deterministic Telemetry Simulator & Anomaly Matrix
Provides zero-hardware benchmark and automated test capability with 7 repeatable anomaly scenarios:
1. `NORMAL`: Baseline desk rest ($A_z \approx 9.81\text{ m/s}^2$, $V_{cc} \approx 3.3\text{V}$, realistic Gaussian noise).
2. `FREE_FALL`: Zero-G drop ($|A| < 1.5\text{ m/s}^2$ for ~800ms) followed by deceleration shock impulse.
3. `HIGH_G_IMPACT`: Violent collision deceleration peak ($>40\text{ m/s}^2$).
4. `TUMBLE_SPIN`: Severe angular rate excursion ($>500^\circ\text{/s}$).
5. `SENSOR_FREEZE`: Simulated I2C lockup with static flatline values and `FROZEN` status.
6. `THERMAL_SPIKE`: Internal junction heating exceeding $65^\circ\text{C}$.
7. `BROWNOUT`: Supply rail voltage dip below $2.5\text{V}$.

### 3. Rule-Based Anomaly Detection & Ghost Trace
* Evaluates sliding telemetry windows with configurable persistence and hysteresis.
* **Ghost Trace Ring Buffer**: Captures a 200-frame forensic circular buffer around each breach, preserving the exact physics trajectory preceding an incident.

### 4. Local AI Diagnostic Interrogator & Ollama Setup
* **Provider Abstraction**: Decoupled interface supporting local open-weight LLMs via Ollama (`llama3.2:1b`, `llama3.2:3b`, `qwen2.5`) with a deterministic, physics-grounded **Forensic Rule Engine** offline fallback.
* **Structured Output Schema**:
  1. Observed physical facts (with exact numerical citations).
  2. Ranked physical hypotheses with confidence percentages.
  3. Actionable engineering bench tests (I2C clock line verification, wiring harness strain relief, MEMS die 1G static test).
  4. Uncertainty boundaries.
* **Ollama Configuration (Optional)**:
  ```bash
  # Install Ollama from https://ollama.ai/ and pull a lightweight model:
  ollama pull llama3.2:1b
  # Run Ollama (listens by default on http://localhost:11434):
  ollama serve
  ```
  If Ollama is not running, GHOST.OS automatically engages its internal deterministic forensic reasoning engine without interruption.

### 5. Digital Afterlife Session Recording & Replay
* Saves diagnostic sessions to timestamped `.jsonl` files in `data/sessions/`.
* Replays past sessions through the live telemetry pipeline with play, pause, single-step, and $0.5\times$ to $4.0\times$ speed multipliers.

---

## Quickstart & Execution

### Prerequisites
* Python 3.10+ (tested on Python 3.13)
* Windows, Linux, or macOS

### 1. Installation
```bash
# Clone repository
git clone https://github.com/debashis-sharingan-21/ghost-os.git
cd ghost-os

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running GHOST.OS
```bash
# Start the telemetry server and web terminal
python run_ghost_os.py --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in any modern browser (Chrome, Edge, Firefox).

### 3. Running Automated Tests
```bash
pytest -v
```
All 34 automated unit and integration tests run in ~6 seconds.

---

## ESP32 Hardware Wiring (Optional)

| MPU6050 Pin | ESP32 Pin | Function | Notes |
|:-----------:|:---------:|:--------:|:------|
| **VCC**     | **3V3**   | Power    | Stable 3.3V DC rail |
| **GND**     | **GND**   | Ground   | Common ground |
| **SCL**     | **GPIO 22**| I2C SCL | 400 kHz Fast-Mode (4.7kΩ pull-up) |
| **SDA**     | **GPIO 21**| I2C SDA | 400 kHz Fast-Mode (4.7kΩ pull-up) |
| **AD0**     | **GND**   | Address  | Default address `0x68` |

The ESP32 firmware source code is located in `firmware/` and can be compiled using [PlatformIO](https://platformio.org/):
```bash
cd firmware
pio run -e esp32dev
pio run -e esp32dev -t upload
```

---

## Current Status & Verification Boundaries

* **Simulated Telemetry, Protocol & Dashboard**: Fully implemented and verified.
* **Deterministic Anomaly Detection & Ghost Trace**: Fully verified with 34 automated tests.
* **AI Provider Abstraction & Offline Fallback**: Fully verified. (Local Ollama LLM integration is supported when Ollama is running on port 11434; deterministic forensic reasoner operates as autonomous offline fallback).
* **ESP32 Firmware Target**: Implemented for ESP32-WROOM-32 with register-level MPU6050 driver; physical hardware flashing requires host USB connection.

---

## License & Attribution

MIT License — Copyright &copy; 2026 debashis-sharingan-21.  
Designed and architected by `debashis-sharingan-21`.
