#!/usr/bin/env python3
"""
INA228 Sensor Calibration Fix for Solar Monitoring

This script addresses the voltage reading issues by:
1. Fixing the calibration parameters for solar panel monitoring (32V, low current)
2. Adding the missing 'voltage' property alias
3. Testing different calibration scenarios
4. Providing correct sensor configuration for solar applications
"""

import time
import board
import adafruit_ina228
from adafruit_ina228 import ConversionTime, AveragingCount, Mode

def test_sensor_calibration():
    """Test different calibration scenarios to find optimal settings for solar monitoring"""
    
    print("🔧 INA228 Solar Monitor Calibration Test")
    print("=" * 50)
    
    try:
        # Initialize sensor
        i2c = board.I2C()
        ina228 = adafruit_ina228.INA228(i2c)
        
        print(f"✅ Sensor connected successfully!")
        print(f"📋 Device ID: 0x{ina228.device_id:X}")
        print()
        
        # Test different calibration scenarios
        calibration_tests = [
            {
                "name": "Default (High Current)",
                "description": "Default 0.015Ω, 10A - designed for high current applications",
                "shunt_res": 0.015,
                "max_current": 10.0,
                "expected": "Very low voltage readings (wrong for solar)"
            },
            {
                "name": "Solar 32V/1A",
                "description": "32V, 1A max - typical solar panel monitoring", 
                "shunt_res": 0.1,
                "max_current": 1.0,
                "expected": "Correct voltage readings for solar panels"
            },
            {
                "name": "Solar 32V/2A", 
                "description": "32V, 2A max - higher current solar monitoring",
                "shunt_res": 0.015,
                "max_current": 2.0,  # Lower than default 10A
                "expected": "Good balance for higher current solar systems"
            },
            {
                "name": "Solar 16V/400mA",
                "description": "16V, 400mA - low voltage solar systems",
                "shunt_res": 0.1,
                "max_current": 0.4,
                "expected": "Optimized for 12V solar systems"
            }
        ]
        
        for i, test in enumerate(calibration_tests, 1):
            print(f"\n🧪 Test {i}: {test['name']}")
            print(f"📝 {test['description']}")
            print(f"💡 Expected: {test['expected']}")
            print("-" * 40)
            
            # Apply calibration
            ina228.set_calibration(test['shunt_res'], test['max_current'])
            time.sleep(0.1)  # Allow sensor to settle
            
            # Take multiple readings for stability
            voltages = []
            currents = []
            powers = []
            
            for _ in range(5):
                voltages.append(ina228.bus_voltage)
                currents.append(ina228.current * 1000)  # Convert to mA
                powers.append(ina228.power * 1000)      # Convert to mW
                time.sleep(0.1)
            
            avg_voltage = sum(voltages) / len(voltages)
            avg_current = sum(currents) / len(currents) 
            avg_power = sum(powers) / len(powers)
            
            print(f"🔋 Bus Voltage: {avg_voltage:.3f} V")
            print(f"⚡ Current: {avg_current:.1f} mA") 
            print(f"🔌 Power: {avg_power:.1f} mW")
            print(f"🌡️  Temperature: {ina228.die_temperature:.1f}°C")
            print(f"⚙️  Shunt Resistance: {test['shunt_res']}Ω")
            print(f"📊 Max Current: {test['max_current']}A")
            
            # Evaluate if this looks like a reasonable solar voltage
            if avg_voltage > 5.0:  # Should be at least 5V for solar panels
                print("✅ Voltage readings look reasonable for solar monitoring!")
            else:
                print("❌ Voltage readings too low for solar applications")
        
        print("\n" + "=" * 50)
        print("🎯 RECOMMENDATION:")
        print("For solar panel monitoring, use:")
        print("• ina228.set_calibration(0.1, 1.0)  # 32V, 1A max")
        print("• This should provide accurate voltage readings for 12-24V solar panels")
        print()
        print("🔧 Additional optimizations for solar monitoring:")
        print("• Use higher averaging for stable readings")
        print("• Set appropriate conversion times for accuracy vs speed")
        
        # Apply recommended calibration and show optimized settings
        print("\n🚀 Applying recommended solar monitoring configuration...")
        ina228.set_calibration(0.1, 1.0)  # 32V, 1A max
        ina228.averaging_count = AveragingCount.COUNT_64  # More averaging for stability
        ina228.bus_voltage_conv_time = ConversionTime.TIME_1052_US  # Longer conversion for accuracy
        ina228.shunt_voltage_conv_time = ConversionTime.TIME_1052_US
        ina228.temp_conv_time = ConversionTime.TIME_1052_US
        
        time.sleep(0.2)  # Allow settings to apply
        
        print("📊 Optimized readings:")
        print(f"🔋 Voltage: {ina228.bus_voltage:.3f} V")
        print(f"⚡ Current: {ina228.current*1000:.1f} mA")
        print(f"🔌 Power: {ina228.power*1000:.1f} mW")
        print(f"🌡️  Temp: {ina228.die_temperature:.1f}°C")
        print(f"📈 Averaging: {ina228.averaging_count} samples")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

def add_voltage_alias():
    """Patch the INA228 class to add the missing 'voltage' property alias"""
    
    def voltage_property(self):
        """Alias for bus_voltage to match official examples"""
        return self.bus_voltage
    
    # Add the property to the class
    adafruit_ina228.INA228.voltage = property(voltage_property)
    print("✅ Added 'voltage' property alias to INA228 class")

if __name__ == "__main__":
    # Add the missing voltage alias first
    add_voltage_alias()
    
    # Test calibration scenarios
    test_sensor_calibration()
    
    print("\n🎉 Calibration test complete!")
    print("💡 Use these settings in your solar monitoring application for accurate readings.")
