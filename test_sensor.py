#!/usr/bin/env python3
"""
Simple test script for INA228 sensor
Run this after setup to verify the sensor is working
"""

try:
    import board
    import adafruit_ina228
    
    print("🔌 Initializing INA228 sensor...")
    i2c = board.I2C()
    ina228 = adafruit_ina228.INA228(i2c)
    
    print("✅ INA228 sensor connected successfully!")
    print("\n📊 Sensor readings:")
    print(f"   Bus Voltage: {ina228.bus_voltage:.3f} V")
    print(f"   Shunt Voltage: {ina228.shunt_voltage * 1000000:.2f} µV")
    print(f"   Current: {ina228.current * 1000:.2f} mA")
    print(f"   Power: {ina228.power * 1000:.2f} mW")
    print(f"   Energy: {ina228.energy:.3f} J")
    print(f"   Charge: {ina228.charge:.3f} C")
    
except ImportError as e:
    print("❌ Missing dependencies. Make sure virtual environment is activated and packages are installed.")
    print(f"Error: {e}")
    print("\nRun: source .venv/bin/activate && pip install -r requirements.txt")
    
except Exception as e:
    print("❌ Sensor connection failed.")
    print(f"Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check I2C is enabled: sudo raspi-config")
    print("2. Check wiring connections")
    print("3. Verify sensor address: sudo i2cdetect -y 1")
