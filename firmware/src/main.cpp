// GHOST.OS — ESP32 Telemetry Engine (ghost.v1)
// Non-blocking FreeRTOS telemetry task running at 10 Hz with multi-indicator state machine

#include <Arduino.h>
#include <math.h>
#include "mpu6050_sensor.h"
#include "protocol.h"

#define TELEMETRY_RATE_HZ 10
#define TELEMETRY_PERIOD_MS (1000 / TELEMETRY_RATE_HZ)

// ============================================================================
// HARDWARE PIN DEFINITIONS & CONFIGURATION
// ============================================================================

// 1. External Indicator LED: GPIO 4 (green LED with series resistor)
#define PIN_LED_EXTERNAL         4
#define LED_EXTERNAL_ACTIVE_HIGH true

// 2. Built-in ESP32 DevKit LED: GPIO 2 (standard blue LED on ESP32-WROOM-32 DevKit)
// Configurable: Set to -1 to disable built-in LED control
#define PIN_LED_BUILTIN          2
#define LED_BUILTIN_ACTIVE_HIGH  true

// 3. Audio Buzzer: GPIO 25 (DAC1 / Digital GPIO)
#define PIN_BUZZER               25

// Buzzer Type Configuration:
// - false = Active Buzzer (built-in oscillator, DC driven via digital HIGH/LOW)
// - true  = Passive Buzzer (requires PWM/tone modulation via ESP32 LEDC timer)
#define BUZZER_IS_PASSIVE        false

// Active Buzzer Drive Polarity:
// - true  = Active HIGH (GPIO HIGH turns buzzer ON; rests at LOW / 0V when silent)
// - false = Active LOW (Inverted / open-collector drive; rests at HIGH when silent)
#define BUZZER_ACTIVE_HIGH       true

// Passive Buzzer PWM Parameters (applied only when BUZZER_IS_PASSIVE is true)
#define BUZZER_PWM_CHANNEL       0
#define BUZZER_PWM_TIMER_BITS    8
#define BUZZER_TONE_WARN_HZ      2000   // 2.0 kHz warning tone
#define BUZZER_TONE_CRIT_HZ      2700   // 2.7 kHz piercing alert tone
#define BUZZER_TONE_ERR_HZ       1500   // 1.5 kHz fault chirp

// ============================================================================
// SYSTEM STATES & THRESHOLDS
// ============================================================================

enum SystemState {
    STATE_NORMAL = 0,
    STATE_WARNING = 1,
    STATE_CRITICAL = 2,
    STATE_SENSOR_DISCONNECTED = 3
};

// Alert persistence durations (minimum alert hold time in milliseconds)
#define ALERT_HOLD_MS_CRITICAL   1500
#define ALERT_HOLD_MS_WARNING    1000

// Anomaly thresholds calibrated to match GHOST.OS deterministic rule standards.
// High thresholds ensure normal bench handling / tilting never triggers false alerts:
#define THRESHOLD_FREE_FALL_MAG      2.0f    // m/s^2 (near zero-G, persistence >= 2 frames)
#define THRESHOLD_HIGH_G_IMPACT_MAG 35.0f    // m/s^2 (severe kinetic impact / collision)
#define THRESHOLD_WARN_SHOCK_MAG    22.0f    // m/s^2 (elevated kinetic disturbance)
#define THRESHOLD_WARN_GYRO_RATE   400.0f    // deg/s (uncontrolled high-speed tumble)
#define THRESHOLD_THERMAL_HIGH      55.0f    // °C (elevated die temperature)
#define THRESHOLD_THERMAL_LOW      -10.0f    // °C (sub-zero thermal fault)

// ============================================================================
// HARDWARE INSTANCES & RUNTIME STATE
// ============================================================================

static MPU6050Sensor s_imu(21, 22, 0x68);
static uint32_t s_seq = 0;
static const char* DEVICE_ID = "ESP32-GHOST-HW01";

static volatile SystemState s_current_state = STATE_NORMAL;

// ============================================================================
// HARDWARE ACTUATION ROUTINES
// ============================================================================

/**
 * Synchronously drives external and built-in LEDs according to configured polarity.
 */
static void setLeds(bool on) {
    uint8_t ext_val = on ? (LED_EXTERNAL_ACTIVE_HIGH ? HIGH : LOW) 
                         : (LED_EXTERNAL_ACTIVE_HIGH ? LOW : HIGH);
    digitalWrite(PIN_LED_EXTERNAL, ext_val);

    if (PIN_LED_BUILTIN >= 0) {
        uint8_t int_val = on ? (LED_BUILTIN_ACTIVE_HIGH ? HIGH : LOW) 
                             : (LED_BUILTIN_ACTIVE_HIGH ? LOW : HIGH);
        digitalWrite(PIN_LED_BUILTIN, int_val);
    }
}

/**
 * Controls buzzer output with explicit safety bounds:
 * - Supports active buzzers (DC drive) and passive buzzers (LEDC PWM).
 * - Enforces digital LOW (0V) output whenever inactive.
 */
static void setBuzzerOutput(bool active, uint32_t frequency = 2400) {
    if (BUZZER_IS_PASSIVE) {
#if defined(ESP32)
        if (active && frequency > 0) {
            ledcWriteTone(BUZZER_PWM_CHANNEL, frequency);
        } else {
            ledcWriteTone(BUZZER_PWM_CHANNEL, 0);
            ledcWrite(BUZZER_PWM_CHANNEL, 0);
            digitalWrite(PIN_BUZZER, LOW);
        }
#endif
    } else {
        if (active) {
            digitalWrite(PIN_BUZZER, BUZZER_ACTIVE_HIGH ? HIGH : LOW);
        } else {
            digitalWrite(PIN_BUZZER, BUZZER_ACTIVE_HIGH ? LOW : HIGH);
        }
    }
}

/**
 * Non-blocking indicator state machine executing on every loop() pass:
 * - NORMAL: Synchronized dual heartbeat pulse; buzzer silent.
 * - WARNING: 600ms warning blink; short 60ms intermittent beeps.
 * - CRITICAL: 250ms fast alert strobe; rapid 70ms distinguishable alert beeps.
 * - SENSOR DISCONNECTED: Triple rapid flash burst; short double-chirp error pattern.
 */
static void updateIndicators(uint32_t now) {
    bool led_on = false;
    bool buzzer_on = false;
    uint32_t tone_freq = 0;

    switch (s_current_state) {
        case STATE_NORMAL: {
            // Heartbeat pattern: Dual pulse every 1000ms
            // 0-80ms ON, 80-200ms OFF, 200-280ms ON, 280-1000ms OFF
            uint32_t cycle = now % 1000;
            if (cycle < 80 || (cycle >= 200 && cycle < 280)) {
                led_on = true;
            } else {
                led_on = false;
            }
            buzzer_on = false;
            break;
        }

        case STATE_WARNING: {
            // Distinct warning pattern: 600ms cycle
            // LEDs: 250ms ON / 350ms OFF
            // Buzzer: Short intermittent 60ms beep at cycle start (10% duty cycle)
            uint32_t cycle = now % 600;
            led_on = (cycle < 250);
            buzzer_on = (cycle < 60);
            tone_freq = BUZZER_TONE_WARN_HZ;
            break;
        }

        case STATE_CRITICAL: {
            // Fast critical alert pattern: 250ms cycle
            // LEDs: 125ms ON / 125ms OFF (rapid urgent strobe)
            // Buzzer: 70ms ON / 180ms OFF (distinctive rapid alarm cadence)
            uint32_t cycle = now % 250;
            led_on = (cycle < 125);
            buzzer_on = (cycle < 70);
            tone_freq = BUZZER_TONE_CRIT_HZ;
            break;
        }

        case STATE_SENSOR_DISCONNECTED: {
            // Sensor fault: 1500ms cycle
            // LEDs: Triple rapid flash burst (60ms ON/60ms OFF x3)
            // Buzzer: Short double-chirp error pattern (50ms ON, 50ms OFF, 50ms ON), then silent for 1350ms
            uint32_t cycle = now % 1500;
            if (cycle < 360) {
                uint32_t burst_phase = cycle % 120;
                led_on = (burst_phase < 60);
            } else {
                led_on = false;
            }

            if ((cycle < 50) || (cycle >= 100 && cycle < 150)) {
                buzzer_on = true;
                tone_freq = BUZZER_TONE_ERR_HZ;
            } else {
                buzzer_on = false;
            }
            break;
        }
    }

    setLeds(led_on);
    setBuzzerOutput(buzzer_on, tone_freq);
}

// ============================================================================
// ARDUINO SETUP
// ============================================================================

void setup() {
    // Configure External LED (GPIO 4)
    pinMode(PIN_LED_EXTERNAL, OUTPUT);
    digitalWrite(PIN_LED_EXTERNAL, LED_EXTERNAL_ACTIVE_HIGH ? LOW : HIGH);

    // Configure Built-in LED (GPIO 2, if enabled)
    if (PIN_LED_BUILTIN >= 0) {
        pinMode(PIN_LED_BUILTIN, OUTPUT);
        digitalWrite(PIN_LED_BUILTIN, LED_BUILTIN_ACTIVE_HIGH ? LOW : HIGH);
    }

    // Configure Buzzer (GPIO 25)
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
    if (BUZZER_IS_PASSIVE) {
#if defined(ESP32)
        ledcSetup(BUZZER_PWM_CHANNEL, 2000, BUZZER_PWM_TIMER_BITS);
        ledcAttachPin(PIN_BUZZER, BUZZER_PWM_CHANNEL);
        ledcWrite(BUZZER_PWM_CHANNEL, 0);
#endif
    }

    Serial.begin(115200);
    delay(500); // Allow power rail and USB UART bridge to stabilize

    // Initial diagnostic banner
    Serial.println("{\"proto\":\"ghost.v1\",\"status\":\"BOOTING\",\"device_id\":\"ESP32-GHOST-HW01\"}");

    if (s_imu.begin()) {
        Serial.println("{\"proto\":\"ghost.v1\",\"status\":\"CALIBRATING\",\"device_id\":\"ESP32-GHOST-HW01\"}");
        s_imu.calibrate(150);
        Serial.println("{\"proto\":\"ghost.v1\",\"status\":\"ONLINE\",\"device_id\":\"ESP32-GHOST-HW01\"}");
    } else {
        s_current_state = STATE_SENSOR_DISCONNECTED;
        Serial.println("{\"proto\":\"ghost.v1\",\"status\":\"SENSOR_NOT_DETECTED\",\"device_id\":\"ESP32-GHOST-HW01\",\"error\":8}");
    }
}

// ============================================================================
// MAIN TELEMETRY LOOP (100% NON-BLOCKING, ZERO DELAY)
// ============================================================================

void loop() {
    uint32_t now = millis();

    // 1. Update non-blocking indicator state machine on every pass
    updateIndicators(now);

    // 2. Dispatch telemetry at exact 10 Hz rate without blocking
    static uint32_t last_tick = 0;
    static uint32_t last_hz_calc = 0;
    static uint32_t frame_count = 0;
    static float current_hz = 10.0f;

    // Alert hold timers & persistence counters
    static uint32_t crit_until = 0;
    static uint32_t warn_until = 0;
    static uint8_t free_fall_consecutive = 0;

    if (now - last_tick < TELEMETRY_PERIOD_MS) {
        // Return immediately to keep updateIndicators() responsive
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

    // Sample MPU6050
    MPUData mpu;
    bool ok = s_imu.sample(mpu);

    // Evaluate hardware status and anomaly state
    if (!s_imu.isInitialized() || !ok || mpu.error_code == 0x08 || (mpu.status && strcmp(mpu.status, "FAIL") == 0)) {
        s_current_state = STATE_SENSOR_DISCONNECTED;
        mpu.error_code = 0x08;
        mpu.status = "FAIL";
    } else {
        // Sensor communicating normally

        // Check Free Fall: persistent near-zero gravity (< 2.0 m/s^2 for >= 2 consecutive frames)
        if (mpu.amag < THRESHOLD_FREE_FALL_MAG) {
            free_fall_consecutive++;
        } else {
            free_fall_consecutive = 0;
        }

        bool is_free_fall = (free_fall_consecutive >= 2);
        bool is_high_g = (mpu.amag >= THRESHOLD_HIGH_G_IMPACT_MAG);
        bool is_frozen = (mpu.status && strcmp(mpu.status, "FROZEN") == 0);

        if (is_free_fall || is_high_g || is_frozen) {
            crit_until = now + ALERT_HOLD_MS_CRITICAL;
            if (is_high_g) mpu.error_code = 0x01;
            else if (is_free_fall) mpu.error_code = 0x02;
            else mpu.error_code = 0x03;
        }

        // Check Warning conditions
        float max_gyro = fmaxf(fabsf(mpu.gx), fmaxf(fabsf(mpu.gy), fabsf(mpu.gz)));
        bool is_tumble = (max_gyro >= THRESHOLD_WARN_GYRO_RATE);
        bool is_elevated_shock = (mpu.amag >= THRESHOLD_WARN_SHOCK_MAG && mpu.amag < THRESHOLD_HIGH_G_IMPACT_MAG);
        bool is_thermal = (mpu.temp_c > THRESHOLD_THERMAL_HIGH || mpu.temp_c < THRESHOLD_THERMAL_LOW);

        if (is_tumble || is_elevated_shock || is_thermal) {
            warn_until = now + ALERT_HOLD_MS_WARNING;
            if (mpu.error_code == 0) {
                if (is_tumble) mpu.error_code = 0x04;
                else if (is_elevated_shock) mpu.error_code = 0x05;
                else mpu.error_code = 0x06;
            }
        }

        // Resolve active system state from hold timers
        if (now < crit_until) {
            s_current_state = STATE_CRITICAL;
        } else if (now < warn_until) {
            s_current_state = STATE_WARNING;
        } else {
            s_current_state = STATE_NORMAL;
            mpu.error_code = 0;
        }
    }

    // Assemble system health telemetry
    SystemHealth health;
    health.uptime_ms = now;
    health.free_heap = esp_get_free_heap_size();
    health.vcc_mv = 3300; // Nominal 3.3V rail
    health.loop_hz = current_hz;
    health.wifi_rssi = 0;

    bool anomaly_active = (s_current_state != STATE_NORMAL);

    // Emit ghost.v1 JSON line over serial
    ProtocolEmitter::emitJsonLine(
        Serial,
        ++s_seq,
        DEVICE_ID,
        mpu,
        health,
        anomaly_active
    );
}
