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

# Let's discover what properties are available
print("🔍 Available properties:")
for attr in dir(ina228):
    if not attr.startswith('_') and not callable(getattr(ina228, attr)):
        try:
            value = getattr(ina228, attr)
            print(f"   {attr}: {value}")
        except Exception as e:
            print(f"   {attr}: Error reading - {e}")

print("\n📊 Common measurements:")
try:
    print(f"   Voltage: {ina228.voltage:.3f} V")
except:
    try:
        print(f"   Bus Voltage: {ina228.bus_voltage:.3f} V")
    except:
        print("   Bus Voltage: Not available")

try:
    print(f"   Current: {ina228.current * 1000:.2f} mA")
except:
    print("   Current: Not available")

try:
    print(f"   Power: {ina228.power * 1000:.2f} mW")
except:
    print("   Power: Not available")

try:
    print(f"   Shunt Voltage: {ina228.shunt_voltage * 1000:.3f} mV")
except:
    print("   Shunt Voltage: Not available")

print("🎉 Test complete!")
