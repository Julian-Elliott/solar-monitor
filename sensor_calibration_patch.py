#!/usr/bin/env python3
"""
Patch for INA228 Solar Monitor - Fix Voltage Reading Issue

This script provides:
1. The correct calibration for solar monitoring (0.1Ω, 1A instead of 0.015Ω, 10A)
2. The missing 'voltage' property alias for compatibility
3. Easy integration into existing data loggers

Apply this patch by importing: from sensor_calibration_patch import apply_solar_calibration
"""

import adafruit_ina228


def add_voltage_alias():
    """Add the missing 'voltage' property alias to INA228 class"""
    def voltage_property(self):
        """Alias for bus_voltage to match official examples"""
        return self.bus_voltage
    
    adafruit_ina228.INA228.voltage = property(voltage_property)


def apply_solar_calibration(sensor):
    """
    Apply optimal calibration for solar panel monitoring
    
    Args:
        sensor: INA228 sensor instance
        
    This fixes the voltage reading issue by:
    - Using 0.1Ω shunt resistance instead of 0.015Ω  
    - Setting max current to 1A instead of 10A
    """
    # Apply solar-optimized calibration (32V, 1A max)
    sensor.set_calibration(0.1, 1.0)
    
    # Note: Advanced settings not available in current library version
    # These would be optimal if available:
    # sensor.averaging_count = 64
    # sensor.bus_voltage_conv_time = longer conversion time
    
    return sensor


def init_solar_ina228(i2c):
    """
    Initialize INA228 sensor with solar-optimized settings
    
    Args:
        i2c: I2C bus instance
        
    Returns:
        Properly configured INA228 sensor for solar monitoring
    """
    # Add voltage alias first
    add_voltage_alias()
    
    # Initialize sensor
    sensor = adafruit_ina228.INA228(i2c)
    
    # Apply solar calibration
    apply_solar_calibration(sensor)
    
    return sensor


# Auto-apply voltage alias when module is imported
add_voltage_alias()

print("✅ Solar monitor calibration patch loaded")
print("💡 Use: sensor = init_solar_ina228(i2c) for new sensors")
print("💡 Use: apply_solar_calibration(existing_sensor) for existing sensors")
