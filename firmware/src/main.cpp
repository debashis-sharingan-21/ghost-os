// GHOST.OS — ESP32 Telemetry Engine (ghost.v1)
// Non-blocking FreeRTOS telemetry task running at 10 Hz

#include <Arduino.h>
#include "mpu6050_sensor.h"
#include "protocol.h"

#define TELEMETRY_RATE_HZ 10
#define TELEMETRY_PERIOD_MS (1000 / TELEMETRY_RATE_HZ)

static MPU6050Sensor s_imu(21, 22, 0x68);
static uint32_t s_seq = 0;
static const char* DEVICE_ID = "ESP32-GHOST-HW01";

void setup() {
    Serial.begin(115200);
    delay(500);

    // Initial diagnostic banner
    Serial.println("{\"proto\":\"ghost.v1\",\"status\":\"BOOTING\",\"device_id\":\"ESP32-GHOST-HW01\"}");

    if (s_imu.begin()) {
        Serial.println("{\"proto\":\"ghost.v1\",\"status\":\"CALIBRATING\",\"device_id\":\"ESP32-GHOST-HW01\"}");
        s_imu.calibrate(150);
        Serial.println("{\"proto\":\"ghost.v1\",\"status\":\"ONLINE\",\"device_id\":\"ESP32-GHOST-HW01\"}");
    } else {
        Serial.println("{\"proto\":\"ghost.v1\",\"status\":\"SENSOR_NOT_DETECTED\",\"device_id\":\"ESP32-GHOST-HW01\",\"error\":8}");
    }
}

void loop() {
    static uint32_t last_tick = 0;
    static uint32_t last_hz_calc = 0;
    static uint32_t frame_count = 0;
    static float current_hz = 10.0f;

    uint32_t now = millis();
    if (now - last_tick < TELEMETRY_PERIOD_MS) {
        delay(2);
        return;
    }
    last_tick = now;

    // Calculate actual loop frequency
    frame_count++;
    if (now - last_hz_calc >= 1000) {
        current_hz = (float)frame_count * 1000.0f / (float)(now - last_hz_calc);
        frame_count = 0;
        last_hz_calc = now;
    }

    MPUData mpu;
    bool ok = s_imu.sample(mpu);

    SystemHealth health;
    health.uptime_ms = now;
    health.free_heap = esp_get_free_heap_size();
    health.vcc_mv = 3300; // Nominal 3.3V supply
    health.loop_hz = current_hz;
    health.wifi_rssi = 0;

    bool anomaly = !ok || (mpu.error_code != 0);

    ProtocolEmitter::emitJsonLine(
        Serial,
        ++s_seq,
        DEVICE_ID,
        mpu,
        health,
        anomaly
    );
}
