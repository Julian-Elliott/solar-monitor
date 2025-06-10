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
            # Shunt: 15mΩ, Max current: 10A (fuse rating), but typical max is 3.77A
            self.ina228.set_shunt(self.config.SHUNT_RESISTANCE, self.config.MAX_CURRENT)
            
            self.logger.info(f"✅ PS100 sensor initialized at 0x{self.address:02X}")
            self.logger.info(f"   Shunt: {self.config.SHUNT_RESISTANCE}Ω, Max: {self.config.MAX_CURRENT}A")
        except Exception as e:
            self.logger.error(f"❌ Sensor initialization failed: {e}")
            raise
    
    def read(self) -> Dict[str, Any]:
        """Read sensor data and return structured reading"""
        try:
            # Raw readings
            voltage = float(self.ina228.voltage)  # Bus voltage is correct
            shunt_voltage = float(self.ina228.shunt_voltage)
            
            # Calculate current manually using Ohm's law (more accurate)
            # I = V_shunt / R_shunt
            current = shunt_voltage / self.config.SHUNT_RESISTANCE
            
            # Calculate power manually
            power = voltage * current
            
            # Temperature (fallback if not available)
            temp = float(getattr(self.ina228, 'temperature', 25.0))
            
            # Calculate derived values
            energy_wh = power / 3600.0  # Wh for this second
            efficiency = (power / self.config.RATED_POWER) * 100 if power > 0 else 0
            
            # Determine conditions
            conditions = self._assess_conditions(voltage, current, power)
            
            # Get alert flags if available
            try:
                alerts = self.ina228.alert_flags
                has_alerts = any(alerts.values()) if hasattr(alerts, 'values') else False
            except:
                # Fallback alert checking
                alerts = {
                    'overvoltage': voltage > self.config.MAX_VOLTAGE,
                    'overcurrent': current > self.config.MAX_CURRENT,
                    'power_limit': power > self.config.RATED_POWER * 1.1
                }
                has_alerts = any(alerts.values())
            
            return {
                'timestamp': datetime.now(timezone.utc),
                'voltage': voltage,
                'current': current, 
                'power': power,
                'energy_wh': energy_wh,
                'temperature': temp,
                'efficiency_percent': efficiency,
                'conditions': conditions,
                'alerts': alerts,
                'has_alerts': has_alerts,
                'panel_id': f'PS100_0X{self.address:02X}',
                'shunt_voltage': shunt_voltage  # For debugging
            }
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
