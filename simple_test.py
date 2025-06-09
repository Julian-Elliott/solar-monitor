#!/usr/bin/env python3
"""
Simple INA228 test using the documented API
"""

import board
import adafruit_ina228

print("🔌 Testing INA228 sensor...")
i2c = board.I2C()
ina228 = adafruit_ina228.INA228(i2c)

print("✅ INA228 connected!")
print("📊 Sensor readings (using documented API):")

try:
    print(f"   Voltage: {ina228.voltage:.3f} V")
    print(f"   Current: {ina228.current:.3f} A")  # Note: in Amperes, not mA
    print(f"   Power: {ina228.power:.3f} W")      # Note: in Watts, not mW
    print(f"   Shunt Voltage: {ina228.shunt_voltage*1000000:.2f} µV")
    print(f"   Temperature: {ina228.temperature:.1f} °C")
except Exception as e:
    print(f"❌ Error: {e}")
    print("Let me try the old naming convention...")
    try:
        print(f"   Bus Voltage: {ina228.bus_voltage:.3f} V")
        print(f"   Current: {ina228.current:.3f} mA")
        print(f"   Power: {ina228.power:.3f} mW")
    except Exception as e2:
        print(f"❌ Also failed: {e2}")

print("🎉 Test complete!")
