# GHOST.OS Hardware & Sensor Wiring Guide

## 1. Supported Hardware Target
* **Microcontroller**: ESP32-WROOM-32 / ESP32-DevKitC (Xtensa Dual-Core 240 MHz)
* **Primary Sensor**: MPU6050 (InvenSense 6-Axis MotionTracking: 3-Axis Gyroscope + 3-Axis Accelerometer + Digital Motion Processor / Internal Temp Sensor)
* **Communication Interface**: I2C Bus @ 400 kHz (Fast Mode) / 100 kHz (Standard Mode)
* **Telemetry Link**: USB UART @ 115200 8-N-1 (Default)

---

## 2. Wiring & Pinout Diagram

| MPU6050 Pin | ESP32-WROOM-32 Pin | Function | Notes |
|:-----------:|:------------------:|:--------:|:------|
| **VCC**     | **3V3** (or 5V with on-board LDO) | Power Supply | MPU6050 breakout boards typically include a 3.3V LDO; feed 3.3V or 5V. |
| **GND**     | **GND**            | Ground   | Common ground reference. |
| **SCL**     | **GPIO 22**        | I2C Clock| Default ESP32 hardware I2C SCL. Requires 4.7kΩ pull-up to 3.3V (often integrated on breakout). |
| **SDA**     | **GPIO 21**        | I2C Data | Default ESP32 hardware I2C SDA. Requires 4.7kΩ pull-up to 3.3V. |
| **AD0**     | **GND** (0x68) / **3V3** (0x69) | I2C Address Select | Pull to GND for address `0x68` (default); pull to 3V3 for `0x69`. |
| **INT**     | **GPIO 19** (Optional) | Data Ready Interrupt | Optional hardware motion trigger interrupt. |

---

## 3. Power & Signal Integrity Requirements
1. **Supply Voltage**: Stable 3.3V DC rail. Brownouts below 2.7V will trigger sensor resets or invalid ADC conversions.
2. **I2C Bus Length**: Keep wiring $< 20\text{ cm}$ to avoid parasitic capacitance on high-speed 400 kHz I2C clock.
3. **Decoupling**: Ensure a $0.1\,\mu\text{F}$ ceramic capacitor is situated adjacent to the MPU6050 VCC/GND pins to filter switching noise from the ESP32 Wi-Fi radio.

---

## 4. Hardware Diagnostic Indicators
* **Sensor Online**: Status = `"OK"`, calibrated bias active.
* **Sensor Missing / Disconnected**: WHO_AM_I register read fails (expected `0x68` or `0x72`). Status emitted as `"FAIL"`, error code `0x08`. Firmware does NOT freeze or hallucinate valid data.
* **Bus Lockup (SDA held low)**: I2C timeout recovery sequence toggles SCL 9 times to unstick slave state machine.
