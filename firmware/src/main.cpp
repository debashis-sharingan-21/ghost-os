// GHOST.OS — ESP32 Telemetry Engine (ghost.v1)
// Non-blocking FreeRTOS telemetry task running at 10 Hz

#include <Arduino.h>
#include "mpu6050_sensor.h"
#include "protocol.h"

#define TELEMETRY_RATE_HZ 10
#define TELEMETRY_PERIOD_MS (1000 / TELEMETRY_RATE_HZ)

// Status LED Pin: GPIO 4 is confirmed safe, non-strapping general-purpose output
#define PIN_STATUS_LED 4

static MPU6050Sensor s_imu(21, 22, 0x68);
static uint32_t s_seq = 0;
static const char* DEVICE_ID = "ESP32-GHOST-HW01";

/**
 * Non-blocking indicator LED state machine (Zero delay, deterministic timing)
 * - Sensor Disconnected: 3 rapid strobe bursts every 1.2s
 * - Anomaly Active: Fast warning flash (80ms ON / 80ms OFF)
 * - Normal Nominal: Calm heartbeat pulse (100ms ON / 900ms OFF)
 */
static void updateStatusLed(uint32_t now, bool imu_online, bool anomaly_active, uint16_t error_code) {
    static uint32_t last_led_toggle = 0;
    static bool led_state = false;
    static uint32_t last_burst_cycle = 0;

    if (!imu_online || error_code == 8) {
        // Sensor disconnected: Distinct fault pattern (3 rapid 60ms strobes every 1200ms)
        uint32_t cycle_time = now - last_burst_cycle;
        if (cycle_time < 360) {
            uint32_t phase = cycle_time % 120;
            led_state = (phase < 60);
        } else if (cycle_time >= 1200) {
            last_burst_cycle = now;
            led_state = false;
        } else {
            led_state = false;
        }
    } else if (anomaly_active) {
        // Warning / Critical anomaly: Fast blink (80ms ON / 80ms OFF)
        if (now - last_led_toggle >= 80) {
            led_state = !led_state;
            last_led_toggle = now;
        }
    } else {
        // Normal baseline: Slow heartbeat blink (100ms ON / 900ms OFF)
        uint32_t cycle = now % 1000;
        led_state = (cycle < 100);
    }

    digitalWrite(PIN_STATUS_LED, led_state ? HIGH : LOW);
}

void setup() {
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

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

    // Update non-blocking indicator LED
    updateStatusLed(now, s_imu.isInitialized(), anomaly, mpu.error_code);

    ProtocolEmitter::emitJsonLine(
        Serial,
        ++s_seq,
        DEVICE_ID,
        mpu,
        health,
        anomaly
    );
}
