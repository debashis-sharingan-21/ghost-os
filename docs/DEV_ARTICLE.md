---
title: GHOST.OS — The Machine Remembers: Reconstructing Embedded Failures with Local Open-Weight AI
published: true
tags: hacktoberfest, ai, opensource, embedded, python
cover_image: https://raw.githubusercontent.com/debashis-sharingan-21/ghost-os/main/docs/assets/screenshots/command_center.png
canonical_url: https://github.com/debashis-sharingan-21/ghost-os
description: An air-gapped embedded telemetry, deterministic anomaly detector, and post-mortem forensic platform powered by local open-weight AI.
---

# GHOST.OS — The Machine Remembers

> *"Every machine leaves a last transmission. GHOST.OS reconstructs what happened."*

* **Repository**: [https://github.com/debashis-sharingan-21/ghost-os](https://github.com/debashis-sharingan-21/ghost-os)  
* **Challenge Target**: Hacktoberfest Open-Source AI Challenge — Week 4: "Ghost in the Machine"  
* **Author**: Debashis Mohapatra ([@debashis-sharingan-21](https://github.com/debashis-sharingan-21))

---

## 1. The Real Problem: The Black Box Dilemma of the Edge

Imagine an autonomous ground rover operating in a remote mining tunnel or a delivery drone surveying a transmission corridor. Suddenly, an anomalous event occurs: an internal power rail dips, an I²C bus freezes, or a severe kinetic impact tears off a mounting bracket.

In traditional embedded systems, one of two failures occurs:
1. **The Telemetry Truncates**: The microcontroller resets, the Wi-Fi connection drops, or the flash memory buffer corrupts. The diagnostic data logged to the cloud ends several seconds *before* the critical fault.
2. **The Post-Mortem Guesswork**: Engineers are left staring at shattered carbon fiber or frozen registers, guessing whether the fall caused the power loss or the power loss caused the fall.

Generic cloud-connected generative AI does not solve this problem. In mission-critical robotics:
* You cannot send gigabytes of high-frequency sensor streams to a cloud API over an intermittent edge radio.
* You cannot wait seconds for an API round-trip.
* You cannot risk a language model hallucinating physical phenomena (e.g., claiming "ambient gravity collapsed to zero" instead of identifying a structural separation).

We built **GHOST.OS** to solve this: an air-gapped, real-time instrumentation and forensic analysis platform that reconstructs the machine's final transmission using deterministic physics rules and local open-weight AI.

---

## 2. Why the Machine's Last Transmission Matters

When physical hardware fails, the microsecond trajectory preceding the failure contains the entire story of the root cause:
* **True Zero-G Drop**: Acceleration collapses to $< 1.5\,\text{m/s}^2$ across multiple consecutive frames *before* an explosive deceleration spike ($> 40\,\text{g}$).
* **Sensor Lockup**: Sensor register values flatline with zero variance across the window while bus timing ticks continue, pointing to an I²C slave state-machine hang.
* **Supply Rail Collapse**: Voltage drops below $2.5\,\text{V}$ while die temperature spikes, indicating a shorted capacitor or battery cell thermal runaway.

GHOST.OS treats this pre-fault window as sacred empirical evidence.

---

## 3. How Ghost Trace Reconstructs Faults

Rather than beginning to record after an incident is detected (which is always too late), GHOST.OS maintains a continuous **200-frame circular ring buffer in fast memory**:

```
[ Frame N-199 ] ──> [ Frame N-198 ] ──> ... ──> [ Frame N-1 ] ──> [ FAULT DETECTED: Frame N ]
                                                                             │
                                                                             ▼
                                                                ┌────────────────────────┐
                                                                │  GHOST TRACE FREEZE    │
                                                                │  200-Frame Pre-Fault   │
                                                                │  Evidence Bundle Locked│
                                                                └────────────────────────┘
```

When a sliding-window rule breaches a physical safety threshold:
1. The **Ghost Trace Buffer** captures a frozen snapshot of the preceding 20 seconds of continuous 10 Hz physical state ($A_x, A_y, A_z, |A|, G_x, G_y, G_z, T^\circ\text{C}, V_{cc}$, free heap).
2. The engine computes mathematical summary statistics: minimum/maximum vectors, variance, peak angular rates, and supply rail sags.
3. The evidence is packaged into a structured physical prompt with exact numerical citations.

---

## 4. Why We Separate Deterministic Safety from AI Interpretation

A fundamental architectural principle of GHOST.OS is the **absolute separation of deterministic safety detection from probabilistic AI reasoning**:

```
┌────────────────────────────────────────────────────────┐
│             DETERMINISTIC SAFETY TIER                  │
│  Sliding-window rule evaluation (< 100 µs latency)     │
│  Zero false-negative mathematical thresholding         │
│  Hysteresis recovery verification                      │
└──────────────────────────┬─────────────────────────────┘
                           │ Pre-Fault Evidence Bundle
                           ▼
┌────────────────────────────────────────────────────────┐
│           PROBABILISTIC FORENSIC AI TIER               │
│  Local Open-Weight LLM (llama3.2:1b via Ollama)        │
│  Deterministic Offline Forensic Reasoner (Fallback)    │
│  Strictly advisory: NEVER controls GPIO or actuators   │
└────────────────────────────────────────────────────────┘
```

* **The safety engine** determines *that* an anomaly occurred with zero latency and mathematical predictability.
* **The AI engine** analyzes *why* it occurred, ranking physical hypotheses with confidence scores and recommending actionable bench tests for the engineer.
* The AI **never** overrides safety interlocks, writes to microcontroller registers, or actuates hardware.

---

## 5. Local Open-Weight AI & The Air-Gapped Philosophy

GHOST.OS is designed to operate in an underground bunker, an offshore research vessel, or an isolated test bench with zero internet access:

### Primary Engine: Local Open-Weight LLM (`llama3.2:1b`)
Using [Ollama](https://ollama.ai/), GHOST.OS queries a compact, efficient 1-billion parameter open-weight model running on `localhost:11434`. The model receives structured JSON containing:
* Fault onset timestamp and rule identifier.
* Calculated summary statistics (peak deceleration, duration, temperature).
* The 10 most critical frames preceding the breach.

The model returns:
1. **Empirical Physical Facts**: Verifiable numerical citations.
2. **Ranked Physical Hypotheses**: Root causes with confidence percentages.
3. **Actionable Bench Tests**: Specific electrical and mechanical checks (e.g., inspecting 4.7kΩ I²C pull-ups, probing power rail ripple with an oscilloscope).

### Autonomous Offline Fallback: `DeterministicForensicEngine`
If Ollama is not installed, closed, or running on low-resource hardware, GHOST.OS does not crash or throw an API error. It instantly falls back to an internal mathematical rule reasoner that synthesizes structured hypotheses in **under 5 milliseconds**, clearly labeled:
`PROVIDER: DeterministicForensicEngine (ghost-forensic-rule-v1)`.

---

## 6. What Was Technically Difficult

1. **High-Rate Non-Blocking Serial Synchronization**:
   Writing a pySerial connection manager that handles hot-plugging, baud renegotiation, and ESP32 boot noise (`rst:0x1 (POWERON_RESET)...`) without blocking the FastAPI async event loop or dropping telemetry frames required a dedicated daemon worker thread coupled to a thread-safe queue.
2. **Deterministic Multi-Scenario Simulation**:
   Building a 10 Hz simulator that accurately reflects 6-DOF inertial kinematics with realistic Gaussian noise, zero-g ballistic flight, collision impulses, and I²C bus lockups required careful mathematical modeling to ensure reproducible automated test runs.
3. **Air-Gapped 3D Visual Experience**:
   Creating a retro CRT industrial SCADA console with genuine 3D WebGL scenes (procedural wireframe skull with interactive point-light eye pupils, 3D ESP32 and MPU6050 circuit boards with traveling electrical pulses) without loading a single asset from an external CDN or npm registry. Three.js r128 is bundled locally.

---

## 7. Current Verification Status: Tested vs. Untested

We believe in complete transparency:

| Subsystem | Testing Status | Evidence |
| :--- | :---: | :--- |
| **`ghost.v1` Protocol** | **Fully Tested** | 6 unit tests passing; Pydantic model validation verified. |
| **Deterministic Simulator** | **Fully Tested** | 5 unit tests passing; all 7 anomaly scenarios verified. |
| **Anomaly Detection & Ghost Trace** | **Fully Tested** | 8 unit tests passing; circular ring buffer extraction verified. |
| **Offline Forensic Engine** | **Fully Tested** | 2 unit tests passing; sub-5ms structured hypothesis synthesis. |
| **Session Recording & Replay** | **Fully Tested** | 1 unit test passing; timestamped JSONL round-trip verified. |
| **FastAPI & WebSocket Stream** | **Fully Tested** | 8 API tests passing; 10 Hz streaming verified in Chrome/Edge. |
| **Overall Python Test Suite** | **34 Passed (100%)** | `pytest -v` exits with code 0 in 7.48s. |
| **ESP32 Firmware Target** | **Syntactically Verified** | PlatformIO project complete; register drivers and 400 kHz I²C logic verified against ESP-IDF / Arduino core. |
| **Physical Hardware Bench Test** | **Pending** | Target hardware: ESP32-WROOM-32 + MPU6050. Complete 16-step bench procedure documented in `docs/HARDWARE.md` for physical validation. |
| **Live Ollama Inference** | **Pending Host Install** | Architecture fully implemented; tested with mock provider and verified offline fallback. Requires local `ollama serve`. |

---

## 8. Try It Yourself: Quickstart

```bash
# Clone the repository
git clone https://github.com/debashis-sharingan-21/ghost-os.git
cd ghost-os

# Create and activate environment
python -m venv .venv
.\.venv\Scripts\activate   # On Windows
source .venv/bin/activate  # On Linux/macOS

# Install dependencies and launch
pip install -r requirements.txt
python run_ghost_os.py --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in any modern web browser.

---

## Conclusion: The Machine's Ghost

In folklore, a ghost is an echo left behind by an event that refused to be forgotten.

In embedded engineering, **GHOST.OS ensures that when a machine suffers a critical failure, its last physical state is never forgotten**. By combining deterministic safety with local open-weight AI, we turn catastrophic anomalies into structured, actionable engineering intelligence.

* Built with pride for the **Hacktoberfest Open-Source AI Challenge (Week 4: "Ghost in the Machine")**.
* Check out the code, star the repo, and read the hardware guide: [github.com/debashis-sharingan-21/ghost-os](https://github.com/debashis-sharingan-21/ghost-os)
