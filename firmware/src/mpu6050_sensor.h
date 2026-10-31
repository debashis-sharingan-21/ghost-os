#pragma once

#include <Arduino.h>
#include <Wire.h>

struct MPUData {
    float ax;       // m/s^2
    float ay;       // m/s^2
    float az;       // m/s^2
    float amag;     // m/s^2
    float gx;       // deg/s
    float gy;       // deg/s
    float gz;       // deg/s
    float temp_c;   // Celsius
    const char* status; // "OK", "DEGRADED", "FAIL", "FROZEN"
    uint16_t error_code;
    bool calibrated;
};

class MPU6050Sensor {
public:
    MPU6050Sensor(uint8_t sda_pin = 21, uint8_t scl_pin = 22, uint8_t i2c_addr = 0x68);
    
    bool begin();
    bool sample(MPUData& out_data);
    void calibrate(uint16_t samples = 200);
    bool isInitialized() const { return _initialized; }

private:
    uint8_t _sda;
    uint8_t _scl;
    uint8_t _addr;
    bool _initialized;
    bool _calibrated;
    
    // Bias offsets
    float _bias_ax;
    float _bias_ay;
    float _bias_az;
    float _bias_gx;
    float _bias_gy;
    float _bias_gz;

    bool writeReg(uint8_t reg, uint8_t val);
    bool readRegs(uint8_t reg, uint8_t* buf, size_t len);
};
