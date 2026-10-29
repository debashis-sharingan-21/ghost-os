#pragma once

#include <Arduino.h>
#include "mpu6050_sensor.h"

struct SystemHealth {
    uint32_t uptime_ms;
    uint32_t free_heap;
    uint16_t vcc_mv;
    float loop_hz;
    int16_t wifi_rssi;
};

class ProtocolEmitter {
public:
    static void emitJsonLine(
        Print& out,
        uint32_t seq,
        const char* device_id,
        const MPUData& mpu,
        const SystemHealth& health,
        bool anomaly_active
    );
};
