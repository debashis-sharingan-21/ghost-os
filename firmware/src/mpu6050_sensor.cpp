#include "mpu6050_sensor.h"
#include <math.h>

#define MPU_REG_SMPLRT_DIV   0x19
#define MPU_REG_CONFIG       0x1A
#define MPU_REG_GYRO_CONFIG  0x1B
#define MPU_REG_ACCEL_CONFIG 0x1C
#define MPU_REG_ACCEL_XOUT_H 0x3B
#define MPU_REG_PWR_MGMT_1   0x6B
#define MPU_REG_WHO_AM_I     0x75

// Scale factors:
// Accel ±8g -> 4096 LSB/g -> (g / 4096.0) * 9.80665 m/s^2
static const float ACCEL_SCALE = (9.80665f / 4096.0f);
// Gyro ±2000 deg/s -> 16.4 LSB / (deg/s)
static const float GYRO_SCALE = (1.0f / 16.4f);

MPU6050Sensor::MPU6050Sensor(uint8_t sda_pin, uint8_t scl_pin, uint8_t i2c_addr)
    : _sda(sda_pin), _scl(scl_pin), _addr(i2c_addr), _initialized(false), _calibrated(false),
      _bias_ax(0), _bias_ay(0), _bias_az(0), _bias_gx(0), _bias_gy(0), _bias_gz(0) {}

bool MPU6050Sensor::begin() {
    Wire.begin(_sda, _scl, 400000); // 400 kHz Fast-Mode I2C
    Wire.setTimeOut(50);             // 50ms timeout prevents hanging

    uint8_t who = 0;
    if (!readRegs(MPU_REG_WHO_AM_I, &who, 1)) {
        _initialized = false;
        return false;
    }

    // Typical WHO_AM_I is 0x68 (MPU6050) or 0x72 / 0x70 (MPU6500/9250)
    if (who != 0x68 && who != 0x70 && who != 0x72) {
        _initialized = false;
        return false;
    }

    // Wake up from sleep (clear SLEEP bit in PWR_MGMT_1)
    if (!writeReg(MPU_REG_PWR_MGMT_1, 0x01)) return false; // Clock source = Auto Select PLL
    delay(10);

    // Set sample rate divider = 4 (200 Hz internal)
    writeReg(MPU_REG_SMPLRT_DIV, 0x04);
    // Set digital low pass filter (DLPF) to ~44 Hz bandwidth
    writeReg(MPU_REG_CONFIG, 0x03);
    // Set Gyro full scale range to ±2000 deg/s (0x18)
    writeReg(MPU_REG_GYRO_CONFIG, 0x18);
    // Set Accel full scale range to ±8g (0x10)
    writeReg(MPU_REG_ACCEL_CONFIG, 0x10);

    _initialized = true;
    return true;
}

void MPU6050Sensor::calibrate(uint16_t samples) {
    if (!_initialized) return;

    float sum_ax = 0, sum_ay = 0, sum_az = 0;
    float sum_gx = 0, sum_gy = 0, sum_gz = 0;

    for (uint16_t i = 0; i < samples; i++) {
        uint8_t buf[14];
        if (readRegs(MPU_REG_ACCEL_XOUT_H, buf, 14)) {
            int16_t raw_ax = (int16_t)((buf[0] << 8) | buf[1]);
            int16_t raw_ay = (int16_t)((buf[2] << 8) | buf[3]);
            int16_t raw_az = (int16_t)((buf[4] << 8) | buf[5]);
            int16_t raw_gx = (int16_t)((buf[8] << 8) | buf[9]);
            int16_t raw_gy = (int16_t)((buf[10] << 8) | buf[11]);
            int16_t raw_gz = (int16_t)((buf[12] << 8) | buf[13]);

            sum_ax += raw_ax * ACCEL_SCALE;
            sum_ay += raw_ay * ACCEL_SCALE;
            sum_az += raw_az * ACCEL_SCALE;
            sum_gx += raw_gx * GYRO_SCALE;
            sum_gy += raw_gy * GYRO_SCALE;
            sum_gz += raw_gz * GYRO_SCALE;
        }
        delay(3);
    }

    _bias_ax = sum_ax / samples;
    _bias_ay = sum_ay / samples;
    // Expected gravity on Z is ~9.80665 m/s^2 at rest
    _bias_az = (sum_az / samples) - 9.80665f;
    _bias_gx = sum_gx / samples;
    _bias_gy = sum_gy / samples;
    _bias_gz = sum_gz / samples;
    _calibrated = true;
}

bool MPU6050Sensor::sample(MPUData& out) {
    if (!_initialized) {
        // Attempt recovery
        if (!begin()) {
            out.ax = 0.0f;
            out.ay = 0.0f;
            out.az = 0.0f;
            out.amag = 0.0f;
            out.gx = 0.0f;
            out.gy = 0.0f;
            out.gz = 0.0f;
            out.temp_c = -999.0f;
            out.status = "FAIL";
            out.error_code = 0x08; // Sensor hardware missing
            out.calibrated = false;
            return false;
        }
    }

    uint8_t buf[14];
    if (!readRegs(MPU_REG_ACCEL_XOUT_H, buf, 14)) {
        _initialized = false;
        out.status = "FAIL";
        out.error_code = 0x08;
        return false;
    }

    int16_t raw_ax = (int16_t)((buf[0] << 8) | buf[1]);
    int16_t raw_ay = (int16_t)((buf[2] << 8) | buf[3]);
    int16_t raw_az = (int16_t)((buf[4] << 8) | buf[5]);
    int16_t raw_temp = (int16_t)((buf[6] << 8) | buf[7]);
    int16_t raw_gx = (int16_t)((buf[8] << 8) | buf[9]);
    int16_t raw_gy = (int16_t)((buf[10] << 8) | buf[11]);
    int16_t raw_gz = (int16_t)((buf[12] << 8) | buf[13]);

    out.ax = (raw_ax * ACCEL_SCALE) - _bias_ax;
    out.ay = (raw_ay * ACCEL_SCALE) - _bias_ay;
    out.az = (raw_az * ACCEL_SCALE) - _bias_az;
    out.amag = sqrtf(out.ax * out.ax + out.ay * out.ay + out.az * out.az);

    out.gx = (raw_gx * GYRO_SCALE) - _bias_gx;
    out.gy = (raw_gy * GYRO_SCALE) - _bias_gy;
    out.gz = (raw_gz * GYRO_SCALE) - _bias_gz;

    out.temp_c = ((float)raw_temp / 340.0f) + 36.53f;
    out.status = "OK";
    out.error_code = 0;
    out.calibrated = _calibrated;
    return true;
}

bool MPU6050Sensor::writeReg(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(_addr);
    Wire.write(reg);
    Wire.write(val);
    return (Wire.endTransmission() == 0);
}

bool MPU6050Sensor::readRegs(uint8_t reg, uint8_t* buf, size_t len) {
    Wire.beginTransmission(_addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;

    size_t received = Wire.requestFrom((int)_addr, (int)len);
    if (received != len) return false;

    for (size_t i = 0; i < len; i++) {
        buf[i] = Wire.read();
    }
    return true;
}
