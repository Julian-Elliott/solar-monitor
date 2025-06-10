#!/usr/bin/env python3
"""
Anker SOLIX PS100 Optimized Sensor Configuration
Calibrates INA228 for 26.5V, 3.77A (100W) solar panels with 10A fuse protection
"""

import time
import board
import adafruit_ina228

class PS100SensorConfig:
    """Optimized INA228 configuration for Anker SOLIX PS100 panels"""
    
    # PS100 Specifications
    RATED_VOLTAGE = 26.5    # Vmp - Maximum Power Voltage
    RATED_CURRENT = 3.77    # Imp - Maximum Power Current  
    RATED_POWER = 100       # Watts
    OPEN_CIRCUIT_VOLTAGE = 24.5  # Voc
    SHORT_CIRCUIT_CURRENT = 4.1  # Isc
    FUSE_RATING = 10.0      # Your 10A inline fuse
    
    # Optimal INA228 settings for PS100
    SHUNT_RESISTANCE = 0.015  # 15mΩ integrated shunt resistor
    MAX_CURRENT = 10.0       # Match fuse rating
    MAX_VOLTAGE = 30.0       # Above Voc with margin
    
    def __init__(self, i2c, address=0x40):
        """Initialize INA228 with PS100-optimized settings"""
        # Initialize with shunt resistance parameter
        self.ina228 = adafruit_ina228.INA228(i2c, address, self.SHUNT_RESISTANCE)
        self.address = address
        self._configure_for_ps100()
        
    def _configure_for_ps100(self):
        """Apply optimal configuration for PS100 monitoring"""
        print(f"🔧 Configuring INA228 at 0x{self.address:02X} for Anker SOLIX PS100...")
        
        try:
            # Shunt resistance is already set during initialization
            
            # Set averaging for stable readings (solar can fluctuate)
            self.ina228.averaging_count = adafruit_ina228.AveragingCount.COUNT_64
            
            # Set conversion times for good resolution vs speed balance
            self.ina228.conversion_time_bus = adafruit_ina228.ConversionTime.TIME_1052_US
            self.ina228.conversion_time_shunt = adafruit_ina228.ConversionTime.TIME_1052_US
            
            # Configure alerts for PS100 safety limits
            self._configure_alerts()
            
            print("✅ PS100 sensor configuration complete!")
            self._display_config()
            
        except Exception as e:
            print(f"❌ Configuration failed: {e}")
            raise
            
    def _configure_alerts(self):
        """Set up safety alerts for PS100 operation"""
        # Over-current alert at 9.5A (below 10A fuse)
        self.ina228.current_limit = 9.5
        
        # Over-voltage alert at 28V (above normal Voc)
        self.ina228.voltage_limit = 28.0
        
        # Under-voltage alert at 15V (below useful range)
        # Note: This might need adjustment based on your system
        
    def _display_config(self):
        """Display current sensor configuration"""
        print(f"📋 Sensor Configuration (0x{self.address:02X}):")
        print(f"   Shunt Resistance: {self.ina228.shunt_resistance:.3f}Ω")
        print(f"   Max Current Range: ±{self.MAX_CURRENT}A")
        print(f"   Max Voltage Range: {self.MAX_VOLTAGE}V")
        print(f"   Averaging: {self.ina228.averaging_count} samples")
        print(f"   Bus Conv Time: {self.ina228.conversion_time_bus}µs")
        print(f"   Shunt Conv Time: {self.ina228.conversion_time_shunt}µs")
        print(f"   Current Limit: {self.ina228.current_limit}A")
        print(f"   Voltage Limit: {self.ina228.voltage_limit}V")
        
    def read_panel_data(self):
        """Read and return PS100 panel data in proper units"""
        return {
            'voltage': self.ina228.bus_voltage,          # Volts
            'current': self.ina228.current,              # Amps  
            'power': self.ina228.power,                  # Watts
            'energy': self.ina228.energy,                # Joules
            'temperature': self.ina228.die_temperature,  # Celsius
            'shunt_voltage': self.ina228.shunt_voltage,  # Volts across shunt
            'alerts': self.ina228.alert_flags           # Alert status
        }
        
    def validate_readings(self, data):
        """Validate readings are within PS100 expected ranges"""
        issues = []
        
        # Check voltage range
        if data['voltage'] > self.OPEN_CIRCUIT_VOLTAGE + 1.0:
            issues.append(f"Voltage too high: {data['voltage']:.2f}V (max expected: {self.OPEN_CIRCUIT_VOLTAGE}V)")
        elif data['voltage'] < 15.0 and data['current'] > 0.1:
            issues.append(f"Voltage too low for active generation: {data['voltage']:.2f}V")
            
        # Check current range  
        if data['current'] > self.SHORT_CIRCUIT_CURRENT + 0.5:
            issues.append(f"Current too high: {data['current']:.2f}A (max expected: {self.SHORT_CIRCUIT_CURRENT}A)")
        elif data['current'] < 0 and abs(data['current']) > 0.1:
            issues.append(f"Unexpected negative current: {data['current']:.2f}A")
            
        # Check power calculation
        calculated_power = data['voltage'] * data['current']
        if abs(data['power'] - calculated_power) > 1.0:
            issues.append(f"Power calculation mismatch: reported={data['power']:.1f}W, calculated={calculated_power:.1f}W")
            
        return issues
        
    def estimate_conditions(self, data):
        """Estimate solar conditions based on PS100 performance"""
        voltage = data['voltage']
        current = data['current'] 
        power = data['power']
        
        if power > 85:
            return "Excellent - Full sun"
        elif power > 50:
            return "Good - Partial sun" 
        elif power > 15:
            return "Fair - Cloudy"
        elif power > 2:
            return "Poor - Heavy clouds/shade"
        else:
            return "Minimal - Dawn/dusk/shade"

def test_ps100_sensor(address=0x40):
    """Test PS100 sensor configuration and readings"""
    print("🌞 Anker SOLIX PS100 Sensor Test")
    print("=" * 50)
    
    try:
        i2c = board.I2C()
        ps100_sensor = PS100SensorConfig(i2c, address)
        
        print("\n🔄 Taking 10 readings over 20 seconds...")
        
        for i in range(10):
            data = ps100_sensor.read_panel_data()
            conditions = ps100_sensor.estimate_conditions(data)
            issues = ps100_sensor.validate_readings(data)
            
            timestamp = time.strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Reading {i+1}/10:")
            print(f"   Voltage: {data['voltage']:6.2f}V")
            print(f"   Current: {data['current']:6.2f}A") 
            print(f"   Power:   {data['power']:6.1f}W")
            print(f"   Temp:    {data['temperature']:5.1f}°C")
            print(f"   Conditions: {conditions}")
            
            if issues:
                print("   ⚠️  Issues detected:")
                for issue in issues:
                    print(f"      • {issue}")
                    
            if any(data['alerts'].values()):
                active_alerts = [flag for flag, status in data['alerts'].items() if status]
                print(f"   🚨 ALERTS: {', '.join(active_alerts)}")
                
            time.sleep(2)
            
        print("\n✅ PS100 sensor test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    # Test the PS100 sensor configuration
    test_ps100_sensor()
