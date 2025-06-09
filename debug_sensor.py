#!/usr/bin/env python3
"""
Debug script to check available INA228 properties
"""

try:
    import board
    import adafruit_ina228
    
    print("🔌 Initializing INA228 sensor...")
    i2c = board.I2C()
    ina228 = adafruit_ina228.INA228(i2c)
    
    print("✅ INA228 sensor connected successfully!")
    print("\n🔍 Available properties:")
    
    # Test all possible properties
    properties_to_test = [
        'voltage',
        'bus_voltage', 
        'shunt_voltage',
        'current',
        'power',
        'energy',
        'charge',
        'temperature',
        'die_temperature',
        'averaging_count',
        'device_id'
    ]
    
    for prop in properties_to_test:
        try:
            value = getattr(ina228, prop)
            print(f"   ✅ {prop}: {value}")
        except AttributeError:
            print(f"   ❌ {prop}: Not available")
        except Exception as e:
            print(f"   ⚠️  {prop}: Error - {e}")
    
    print("\n📊 Working sensor readings:")
    try:
        print(f"   Bus Voltage: {ina228.bus_voltage:.3f} V")
        print(f"   Shunt Voltage: {ina228.shunt_voltage * 1000000:.2f} µV") 
        print(f"   Current: {ina228.current * 1000:.2f} mA")
        print(f"   Power: {ina228.power * 1000:.2f} mW")
        print(f"   Energy: {ina228.energy:.3f} J")
        print(f"   Charge: {ina228.charge:.3f} C")
    except Exception as e:
        print(f"   Error reading sensors: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")
