"""
PS100 Sensor Interface
Handles INA228 sensor communication and data reading
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

import board
import adafruit_ina228

from ..config import PS100Config


class PS100Sensor:
    """INA228 sensor interface for PS100"""
    
    def __init__(self, address: int = 0x40):
        self.address = address
        self.config = PS100Config()
        self.logger = logging.getLogger(__name__)
        self._setup_sensor()
    
    def _setup_sensor(self):
        """Initialize INA228 with PS100 settings"""
        try:
            i2c = board.I2C()
            self.ina228 = adafruit_ina228.INA228(i2c, self.address)
            
            # Configure for PS100 specifications
            # Use the library's calibration method - closest to our 3.77A max current
            self.ina228.set_calibration_32V_2A()  # This should handle up to 2A well
            
            # Note: shunt_resistance is read-only in this library
            # The calibration method sets it automatically
            
            self.logger.info(f"✅ PS100 sensor initialized at 0x{self.address:02X}")
            self.logger.info(f"   Using calibration: 32V/2A")
            self.logger.info(f"   Actual shunt resistance: {self.ina228.shunt_resistance}Ω")
        except Exception as e:
            self.logger.error(f"❌ Sensor initialization failed: {e}")
            raise
    
    def initialize(self) -> bool:
        """Initialize the sensor (already done in constructor, but needed for compatibility)"""
        try:
            # Test if sensor is working by doing a quick read
            _ = self.ina228.bus_voltage
            return True
        except Exception as e:
            self.logger.error(f"Sensor initialization test failed: {e}")
            return False
    
    def read(self) -> Dict[str, Any]:
        """Read sensor data and return structured reading"""
        try:
            # Raw readings using correct attribute names
            voltage = float(self.ina228.bus_voltage)  # Use bus_voltage not voltage
            shunt_voltage = float(self.ina228.shunt_voltage)
            current = float(self.ina228.current)
            power = float(self.ina228.power)
            
            # Get temperature if available
            temperature = None
            if hasattr(self.ina228, 'die_temperature'):
                try:
                    temperature = float(self.ina228.die_temperature)
                except:
                    pass
            
            # If temperature not available, use a reasonable default
            if temperature is None:
                temperature = 25.0  # Default ambient temperature
            
            # Calculate derived values
            energy_wh = power / 3600.0  # Wh for this second
            efficiency = (power / self.config.RATED_POWER) * 100 if power > 0 else 0
            
            # Determine conditions
            conditions = self._assess_conditions(voltage, current, power)
            
            reading = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'voltage': voltage,
                'current': current,
                'power': power,
                'shunt_voltage': shunt_voltage,
                'temperature': temperature,
                'energy_wh': energy_wh,
                'efficiency': efficiency,
                'conditions': conditions,
                'raw_data': {
                    'bus_voltage': voltage,
                    'shunt_voltage': shunt_voltage,
                    'die_temperature': temperature
                }
            }
            
            self.logger.debug(f"📊 PS100 reading: {power:.3f}W, {voltage:.3f}V, {current:.3f}A")
            return reading
            
        except Exception as e:
            self.logger.error(f"❌ Sensor read failed: {e}")
            return None
    
    def _assess_conditions(self, voltage: float, current: float, power: float) -> str:
        """Assess solar conditions based on readings"""
        if power > 90:
            return "Excellent - Full sun"
        elif power > 50:
            return "Good - Partial sun" 
        elif power > 10:
            return "Poor - Heavy clouds/shade"
        elif voltage < 18:
            return "No generation"
        else:
            return "Poor - Heavy clouds/shade"
