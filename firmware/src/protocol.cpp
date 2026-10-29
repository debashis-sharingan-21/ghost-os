#include "protocol.h"
#include <ArduinoJson.h>

void ProtocolEmitter::emitJsonLine(
    Print& out,
    uint32_t seq,
    const char* device_id,
    const MPUData& mpu,
    const SystemHealth& health,
    bool anomaly_active
) {
    JsonDocument doc;

    doc["proto"] = "ghost.v1";
    doc["seq"] = seq;
    doc["ts_ms"] = (uint64_t)millis();
    doc["device_id"] = device_id;
    doc["simulated"] = false;

    JsonObject mpuObj = doc["mpu6050"].to<JsonObject>();
    mpuObj["accel_x"] = serialized(String(mpu.ax, 3));
    mpuObj["accel_y"] = serialized(String(mpu.ay, 3));
    mpuObj["accel_z"] = serialized(String(mpu.az, 3));
    mpuObj["accel_mag"] = serialized(String(mpu.amag, 3));
    mpuObj["gyro_x"] = serialized(String(mpu.gx, 2));
    mpuObj["gyro_y"] = serialized(String(mpu.gy, 2));
    mpuObj["gyro_z"] = serialized(String(mpu.gz, 2));
    mpuObj["temp_c"] = serialized(String(mpu.temp_c, 2));
    mpuObj["status"] = mpu.status;

    JsonObject healthObj = doc["health"].to<JsonObject>();
    healthObj["uptime_ms"] = health.uptime_ms;
    healthObj["free_heap"] = health.free_heap;
    healthObj["vcc_mv"] = health.vcc_mv;
    healthObj["loop_hz"] = serialized(String(health.loop_hz, 1));
    if (health.wifi_rssi != 0) {
        healthObj["wifi_rssi"] = health.wifi_rssi;
    }

    JsonObject flagsObj = doc["flags"].to<JsonObject>();
    flagsObj["calibrated"] = mpu.calibrated;
    flagsObj["anomaly_active"] = anomaly_active;
    flagsObj["error_code"] = mpu.error_code;

    serializeJson(doc, out);
    out.println();
}
