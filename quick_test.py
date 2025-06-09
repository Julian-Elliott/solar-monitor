#!/usr/bin/env python3
"""
Quick INA228 sensor test - run this to verify everything works
"""

import board
import adafruit_ina228

print("🔌 Testing INA228 sensor...")
i2c = board.I2C()
ina228 = adafruit_ina228.INA228(i2c)

print("✅ INA228 connected!")
print(f"📊 Bus Voltage: {ina228.bus_voltage:.3f} V")
print(f"📊 Current: {ina228.current * 1000:.2f} mA")
print(f"📊 Power: {ina228.power * 1000:.2f} mW")
print(f"📊 Die Temperature: {ina228.die_temperature:.1f} °C")
print("🎉 All working perfectly!")
