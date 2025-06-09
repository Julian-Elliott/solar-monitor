#!/usr/bin/env python3
"""
Solar Monitor - Continuous monitoring of solar panel performance
Uses the INA228 I2C power monitor to track voltage, current, and power
"""

import time
import board
import adafruit_ina228

def main():
    print("🌞 Solar Monitor - Starting up...")
    
    try:
        # Initialize I2C and INA228
        i2c = board.I2C()
        ina228 = adafruit_ina228.INA228(i2c)
        
        print("✅ INA228 sensor connected successfully!")
        print(f"📋 Device Info:")
        print(f"   Manufacturer ID: 0x{ina228.manufacturer_id:04X}")
        print(f"   Averaging: {ina228.averaging_count} samples")
        print(f"   Conversion Times - Bus: {ina228.conversion_time_bus}µs, Shunt: {ina228.conversion_time_shunt}µs")
        print(f"   Temperature: {ina228.temperature:.1f}°C")
        print()
        
        print("🔄 Starting continuous monitoring (Press Ctrl+C to stop)...")
        print("=" * 60)
        
        while True:
            # Read sensor values
            voltage = ina228.voltage
            current = ina228.current
            power = ina228.power
            energy = ina228.energy
            temperature = ina228.temperature
            
            # Convert to more readable units
            current_ma = current * 1000  # Convert to mA
            power_mw = power * 1000      # Convert to mW
            
            # Display readings
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] V: {voltage:6.3f}V | I: {current_ma:7.2f}mA | P: {power_mw:7.2f}mW | E: {energy:6.3f}J | T: {temperature:4.1f}°C")
            
            # Check for any alerts
            flags = ina228.alert_flags
            if any(flags.values()):
                active_alerts = [flag for flag, status in flags.items() if status]
                print(f"⚠️  ALERTS: {', '.join(active_alerts)}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Troubleshooting:")
        print("1. Check I2C wiring connections")
        print("2. Verify sensor address: sudo i2cdetect -y 1")
        print("3. Ensure virtual environment is activated")

if __name__ == "__main__":
    main()
