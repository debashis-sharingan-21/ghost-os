# GHOST.OS — Complete Hardware Bring-Up & Sensor Integration Guide

This guide provides end-to-end instructions for assembling, wiring, flashing, and operating the **ESP32-WROOM-32** microcontroller with an **MPU6050 6-DOF IMU** for the GHOST.OS telemetry platform.

---

## 1. Hardware Bill of Materials (BoM)

| Item | Component | Specification | Quantity | Purpose |
|:---:|:---|:---|:---:|:---|
| **1** | **ESP32 Development Board** | ESP32-WROOM-32 / ESP32-DevKitC (38-pin or 30-pin) | 1 | Microcontroller running FreeRTOS telemetry task |
| **2** | **MPU6050 Sensor Breakout** | GY-521 Breakout (InvenSense 6-DOF IMU + DMP) | 1 | 3-axis accelerometer + 3-axis gyroscope + temp sensor |
| **3** | **USB Data Cable** | Micro-USB or USB-C (Must support DATA, not charge-only) | 1 | Power delivery and 115200 baud UART serial link |
| **4** | **Jumper Wires** | Female-to-Female or DuPont Breadboard Jumper wires | 4 | I²C and power connections (VCC, GND, SDA, SCL) |
| **5** | **Solderless Breadboard** | Half-size or full-size (Optional, but recommended) | 1 | Stable mechanical mounting for static calibration |

---

## 2. Wiring & Electrical Pin Mapping

### Pin Connection Table

| MPU6050 (GY-521) Pin | ESP32-WROOM-32 Pin | Function | Notes & Precautions |
|:---:|:---:|:---:|:---|
| **VCC** | **3V3** | 3.3V DC Power | Connect to ESP32 **3.3V** pin. GY-521 has an onboard 662K 3.3V regulator; feeding 3.3V directly is safe. |
| **GND** | **GND** | Ground | Common ground reference between ESP32 and sensor. |
| **SCL** | **GPIO 22** | I²C Clock | Default hardware I²C SCL line. 400 kHz Fast-Mode. |
| **SDA** | **GPIO 21** | I²C Data | Default hardware I²C SDA line. 400 kHz Fast-Mode. |
| **AD0** | **GND** (or leave floating) | I²C Address Select | Pulled to GND selects default address `0x68`. If pulled to 3.3V, address becomes `0x69`. |
| **INT** | *(Unconnected)* | Motion Interrupt | Optional hardware interrupt pin. Not required for 10 Hz polled stream. |
| **XCL / XDA**| *(Unconnected)* | Auxiliary I²C Master | For external magnetometer (e.g. HMC5883L). Leave unconnected. |

---

## 3. Physical Wiring Schematic Diagram

```
       ┌────────────────────────┐                    ┌────────────────────────┐
       │   ESP32-WROOM-32       │                    │    MPU-6050 (GY-521)   │
       │                        │                    │                        │
       │                   3V3  ├────────────────────┤ VCC                    │
       │                   GND  ├────────────────────┤ GND                    │
       │                        │                    │                        │
       │               GPIO 22  ├────────────────────┤ SCL (I²C Clock)        │
       │               GPIO 21  ├────────────────────┤ SDA (I²C Data)         │
       │                        │                    │                        │
       │                        │              ┌─────┤ AD0 (Address: 0x68)    │
       │                        │              │     │ INT                    │
       │                        │              │     │ XCL                    │
       │                   GND  ├──────────────┘     │ XDA                    │
       └───────────┬────────────┘                    └────────────────────────┘
                   │
                   ▼ Micro-USB / USB-C Data Cable
       ┌────────────────────────┐
       │   HOST PC / LAPTOP     │
       │   (Running GHOST.OS)   │
       └────────────────────────┘
```

---

## 4. Electrical Precautions & Signal Integrity

> [!CAUTION]
> **5V vs 3.3V Logic Levels**: The ESP32 operates strictly at **3.3V logic levels**. Never connect 5V logic directly to GPIO 21 or GPIO 22. While standard GY-521 breakout boards include an onboard low-dropout (LDO) regulator allowing a 5V input on VCC, the I²C bus lines (SDA/SCL) pull up to the board's internal 3.3V rail. Connecting VCC directly to the ESP32's **3V3** pin guarantees logic compatibility.

1. **Pull-Up Resistors**: The GY-521 module includes dual $4.7\,\text{k}\Omega$ pull-up resistors on SDA and SCL to the internal 3.3V rail. **Do not add external pull-up resistors**, as putting resistors in parallel drops the effective resistance too low, causing excessive bus drive current.
2. **Lead Wire Length**: Keep jumper wires shorter than $15\text{ cm}$ (6 inches). Long wires increase parasitic capacitance, rounding the 400 kHz clock edges and triggering I²C bus timeouts.
3. **Decoupling**: Ensure all DuPont jumper connections are seated firmly. An intermittent ground connection will cause WHO_AM_I detection failures (`error_code: 0x08`).

---

## 5. Firmware Architecture & Target Details

The firmware is located in [`firmware/`](file:///c:/Users/Omen/Downloads/ghost-os/firmware/) and is configured for **PlatformIO**:
* **Board Target**: `esp32dev` (Espressif ESP32 Dev Module)
* **Framework**: Arduino / FreeRTOS
* **Baud Rate**: `115200` bps (8-N-1)
* **Telemetry Loop**: Non-blocking 10 Hz ticker (`TELEMETRY_PERIOD_MS = 100`)
* **I²C Driver**: Hardware `TwoWire` initialized via `Wire.begin(21, 22, 400000)` with a 50 ms timeout (`Wire.setTimeOut(50)`), preventing bus lockups if an I²C slave hangs.
* **WHO_AM_I Verification**: Register `0x75` is queried during boot. Expected value: `0x68` (standard MPU-6050) or `0x70`/`0x72` (compatible revisions).
* **Calibration**: 150-sample stationary bias offset calculation subtracting local gravity from the Z-axis.

---

## 6. Software & PlatformIO Setup

### Step 1: Install PlatformIO Core CLI
If PlatformIO is not yet installed on your system, install it using Python:
```powershell
pip install platformio
```
*(Or install the **PlatformIO IDE** extension in Visual Studio Code).*

### Step 2: Identify Your USB COM Port
Connect the ESP32 to your laptop with the USB data cable.
1. Open Windows Device Manager:
   * Press `Win + X` and select **Device Manager**.
   * Expand **Ports (COM & LPT)**.
   * Look for **Silicon Labs CP210x USB to UART Bridge** or **USB-SERIAL CH340**.
   * Note the port number (e.g., `COM3`, `COM4`, or `COM5`).
2. Alternatively, list ports via PlatformIO:
   ```powershell
   pio device list
   ```

### Step 3: Build the Firmware
Open PowerShell in the `firmware` directory:
```powershell
cd C:\Users\Omen\Downloads\ghost-os\firmware
pio run -e esp32dev
```
PlatformIO will automatically download the Espressif32 toolchain, Arduino core, and required libraries (`MPU6050`, `ArduinoJson`), then compile the binary.

### Step 4: Flash Firmware to ESP32
Ensure the serial port is not open in another application:
```powershell
pio run -e esp32dev -t upload
```
*(If the upload hangs at `Connecting........_____`, press and hold the **BOOT** / **IO0** button on the ESP32 board until the flashing progress bar begins).*

### Step 5: Verify via Serial Monitor
Test the output at 115200 baud:
```powershell
pio device monitor -b 115200
```
You should observe newline-delimited JSON Lines streaming at 10 Hz matching the schema below.

---

## 7. Expected `ghost.v1` Telemetry Stream

On boot, the ESP32 emits startup diagnostics followed by continuous frames:

```json
{"proto":"ghost.v1","status":"BOOTING","device_id":"ESP32-GHOST-HW01"}
{"proto":"ghost.v1","status":"CALIBRATING","device_id":"ESP32-GHOST-HW01"}
{"proto":"ghost.v1","status":"ONLINE","device_id":"ESP32-GHOST-HW01"}
{"proto":"ghost.v1","seq":1,"device_id":"ESP32-GHOST-HW01","timestamp":520,"simulated":false,"mpu6050":{"accel_x":0.02,"accel_y":-0.01,"accel_z":9.81,"accel_mag":9.81,"gyro_x":0.1,"gyro_y":0.0,"gyro_z":0.2,"temp_c":26.5,"status":"OK"},"health":{"uptime_ms":520,"free_heap":218400,"vcc_mv":3300,"loop_hz":10.0,"wifi_rssi":0},"flags":{"calibrated":true,"anomaly_active":false,"error_code":0}}
```

> [!IMPORTANT]
> **Close the Serial Monitor**: Always exit the PlatformIO serial monitor (`Ctrl + C` or `Ctrl + ]`) before connecting GHOST.OS. Only one host program can access the COM port at a time.

---

## 8. Connecting GHOST.OS to Physical Hardware

1. Start the GHOST.OS telemetry server:
   ```powershell
   cd C:\Users\Omen\Downloads\ghost-os
   .\.venv\Scripts\python.exe run_ghost_os.py --host 127.0.0.1 --port 8000
   ```
2. Open your browser to **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**.
3. Advance through the **Ghost Gate** and **Hardware Awakening** screens.
4. In the **Command Center**, navigate to the **DEVICE LINK** panel on the left.
5. Click **SCAN** to enumerate active COM ports.
6. In the **INTERFACE / COM PORT** dropdown, select your hardware COM port (e.g. `COM3`).
7. Ensure **BAUD RATE** is set to `115200 bps (Standard)`.
8. Click **CONNECT SERIAL**.
9. The header status badge will instantly transition from `SIMULATION ACTIVE` to **`HARDWARE LINKED`**, and the charts will display live physical accelerometer and gyroscope signals directly from your sensor!

---

## 9. Physical Verification & Bring-Up Checklist

Follow this verified 16-step sequence for hardware validation:

- [ ] **Step 1**: Inspect the GY-521 breakout board; ensure header pins are soldered cleanly without solder bridges.
- [ ] **Step 2**: Wire ESP32 3V3 to MPU6050 VCC, GND to GND, GPIO 21 to SDA, and GPIO 22 to SCL.
- [ ] **Step 3**: Connect the ESP32 to your laptop using a verified USB data cable.
- [ ] **Step 4**: Open Windows Device Manager and confirm the COM port appears under Ports (COM & LPT).
- [ ] **Step 5**: Open terminal in `firmware/` and run `pio run -e esp32dev` to build the firmware.
- [ ] **Step 6**: Flash the board using `pio run -e esp32dev -t upload`.
- [ ] **Step 7**: Verify serial boot messages with `pio device monitor -b 115200`.
- [ ] **Step 8**: Keep the sensor flat and motionless on a desk during the 150-sample calibration phase (~1.5 seconds).
- [ ] **Step 9**: Verify stationary readings: $A_z \approx 9.81\text{ m/s}^2$, $A_x \approx 0.0\text{ m/s}^2$, $A_y \approx 0.0\text{ m/s}^2$, $G \approx 0.0^\circ\text{/s}$.
- [ ] **Step 10**: Tilt the sensor $90^\circ$ onto its edge; verify acceleration shifts from $A_z$ to $A_x$ or $A_y$.
- [ ] **Step 11**: Rotate the sensor smoothly around the Z axis; observe gyro $G_z$ deflections proportional to rotation speed.
- [ ] **Step 12**: Close the serial monitor or any other terminal accessing the COM port.
- [ ] **Step 13**: Launch `python run_ghost_os.py` and open `http://127.0.0.1:8000/`.
- [ ] **Step 14**: In the Device Link panel, select the COM port and click **CONNECT SERIAL**. Confirm the badge shows `HARDWARE LINKED`.
- [ ] **Step 15**: Click **REC SESSION** to record a 15-second physical motion session, then click **STOP REC**.
- [ ] **Step 16**: Switch to **DIGITAL AFTERLIFE REPLAY**, select the recorded physical session, and verify playback in the oscilloscopes!

---

## 10. Hardware Troubleshooting

| Symptom | Probable Cause | Diagnostic & Resolution |
|:---|:---|:---|
| `status: "SENSOR_NOT_DETECTED"`, error: `8` | Loose wiring or wrong I²C address | 1. Check SDA/SCL wires. Ensure SDA is on GPIO 21 and SCL is on GPIO 22.<br>2. Check AD0 pin: if tied to 3.3V, change firmware `MPU6050Sensor s_imu(21, 22, 0x69);`.<br>3. Verify MPU6050 power LED is illuminated. |
| COM port not listed in Device Manager | Missing USB-to-UART driver or charge-only cable | 1. Install [CP210x VCP Drivers](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers) or [WCH CH340 Driver](http://www.wch-ic.com/downloads/CH341SER_EXE.html).<br>2. Replace USB cable with one known to carry data. |
| Telemetry stream freezes after a few seconds | I²C bus lockup due to electrical noise | The firmware includes `Wire.setTimeOut(50)` which automatically resets the bus. If lockups persist, add a $0.1\,\mu\text{F}$ capacitor across VCC/GND directly at the sensor header. |
| Access Denied error when clicking Connect Serial in GHOST.OS | Port is open in another program | Close Arduino Serial Monitor, PuTTY, PlatformIO monitor, or Cura before connecting in GHOST.OS. |
| Stationary Gyroscope reads nonzero values ($>5^\circ\text{/s}$) | Board was moved during boot calibration | Keep the board completely still on a flat table during the 1.5-second boot calibration, or press the ESP32 EN/RST button to recalibrate. |
