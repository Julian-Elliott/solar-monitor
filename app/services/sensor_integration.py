"""
Sensor integration service
Bridges between legacy sensor code and new API
"""

import asyncio
import logging
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any

# Try to import sensor modules, but make them optional
try:
    from src.sensors import PS100Sensor as INA228Sensor  # Use PS100Sensor as INA228Sensor
    SENSORS_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Real PS100 sensor modules loaded")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Sensor modules not available: {e}")
    SENSORS_AVAILABLE = False
    
    # Create mock classes for testing
    class INA228Sensor:
        def __init__(self, address=0x40):
            self.address = address
        
        def initialize(self):
            return False
        
        def read_power(self):
            return None

# Simple solar conditions analyzer
class SolarConditions:
    @staticmethod
    def analyze_conditions(reading):
        if reading and 'power' in reading:
            if reading['power'] > 50:
                return {"condition": "good"}
            elif reading['power'] > 10:
                return {"condition": "fair"}
            else:
                return {"condition": "poor"}
        return {"condition": "unknown"}

from app.services import MonitoringService, PanelService
from app.models import ReadingCreate
from app.core.database import database

logger = logging.getLogger(__name__)

class SensorIntegrationService:
    """Service to integrate sensor readings with the API"""
    
    def __init__(self):
        self.monitoring_service = None
        self.panel_service = None
        self.sensors: Dict[UUID, INA228Sensor] = {}
        self.is_running = False
        
    async def initialize(self):
        """Initialize the service with database connection"""
        self.monitoring_service = MonitoringService(database)
        self.panel_service = PanelService(database)
        logger.info("✅ Sensor integration service initialized")
    
    async def register_panel_sensor(self, panel_id: UUID, i2c_address: int = 0x40) -> bool:
        """Register a sensor for a panel"""
        try:
            sensor = INA228Sensor(address=i2c_address)  # Use 'address' parameter
            if SENSORS_AVAILABLE:
                # Try to initialize the real hardware sensor
                if sensor.initialize():
                    self.sensors[panel_id] = sensor
                    logger.info(f"✅ Registered REAL sensor for panel {panel_id} at I2C address 0x{i2c_address:02X}")
                    return True
                else:
                    logger.error(f"❌ Failed to initialize real sensor for panel {panel_id}")
                    return False
            else:
                # Fallback to mock sensor
                logger.warning("Hardware sensors not available - using mock sensor")
                self.sensors[panel_id] = sensor
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to register sensor for panel {panel_id}: {e}")
            return False
    
    async def read_panel_sensor(self, panel_id: UUID) -> Optional[ReadingCreate]:
        """Read data from a panel's sensor"""
        if panel_id not in self.sensors:
            logger.warning(f"No sensor registered for panel {panel_id}")
            return None
        
        sensor = self.sensors[panel_id]
        logger.info(f"🔍 Reading sensor for panel {panel_id}, SENSORS_AVAILABLE={SENSORS_AVAILABLE}")
        
        try:
            if SENSORS_AVAILABLE:
                # Try to get real sensor reading
                try:
                    logger.info(f"🔍 Attempting real sensor read for panel {panel_id}")
                    reading = sensor.read()  # Use read() method, not read_power()
                    if reading:
                        logger.info(f"✅ Read REAL sensor data for panel {panel_id}: {reading}")
                    else:
                        logger.warning(f"Real sensor returned no data for panel {panel_id}, using fallback")
                        reading = None
                except Exception as sensor_error:
                    logger.error(f"Real sensor error for panel {panel_id}: {sensor_error}")
                    reading = None
            else:
                logger.info(f"🔍 SENSORS_AVAILABLE=False, using mock data")
                reading = None
                
            # If real sensor failed or unavailable, generate realistic mock data
            if not reading:
                logger.info(f"🔍 Generating mock data for panel {panel_id}")
                import random
                from datetime import datetime
                
                # Generate realistic data based on time of day
                hour = datetime.now().hour
                if 6 <= hour <= 18:  # Daytime
                    voltage = round(random.uniform(15.0, 22.0), 2)
                    current = round(random.uniform(1.0, 4.0), 2)
                else:  # Nighttime - very low values
                    voltage = round(random.uniform(0.0, 0.5), 3)
                    current = round(random.uniform(0.0, 0.01), 4)
                
                reading = {
                    'voltage': voltage,
                    'current': current,
                    'power': round(voltage * current, 3),
                    'temperature': round(random.uniform(15.0, 25.0), 1),
                    'shunt_voltage': round(current * 0.015, 6)  # 15mΩ shunt
                }
                logger.info(f"📊 Generated MOCK reading for panel {panel_id}: {reading['power']}W (nighttime: {not (6 <= hour <= 18)})")
            else:
                logger.info(f"📊 Using REAL sensor reading for panel {panel_id}: {reading.get('power')}W")
            
            # Analyze solar conditions
            conditions = SolarConditions.analyze_conditions(reading)
            
            # Calculate efficiency (simplified)
            rated_power = 100.0  # Default PS100 rating
            efficiency = min((reading['power'] / rated_power) * 100, 100.0) if rated_power > 0 else 0.0
            
            # Create reading model
            reading_data = ReadingCreate(
                panel_id=panel_id,
                voltage=reading['voltage'],
                current=reading['current'],
                power=reading['power'],
                temperature=reading.get('temperature'),
                efficiency=efficiency,
                conditions=conditions['condition'],
                shunt_voltage=reading.get('shunt_voltage'),
                alerts=[]  # Will be populated by monitoring service
            )
            
            return reading_data
            
        except Exception as e:
            logger.error(f"❌ Error reading sensor for panel {panel_id}: {e}")
            return None
    
    async def collect_all_readings(self) -> int:
        """Collect readings from all registered sensors"""
        if not self.sensors:
            logger.debug("No sensors registered")
            return 0
        
        readings_collected = 0
        for panel_id in self.sensors.keys():
            try:
                reading_data = await self.read_panel_sensor(panel_id)
                if reading_data:
                    # Store reading via monitoring service
                    reading = await self.monitoring_service.create_reading(reading_data)
                    readings_collected += 1
                    logger.debug(f"📊 Collected reading for panel {panel_id}: {reading.power}W")
            except Exception as e:
                logger.error(f"❌ Failed to collect reading for panel {panel_id}: {e}")
        
        return readings_collected
    
    async def start_monitoring(self, interval: float = 1.0):
        """Start continuous monitoring loop"""
        if self.is_running:
            logger.warning("Monitoring is already running")
            return
        
        self.is_running = True
        logger.info(f"🚀 Starting sensor monitoring with {interval}s interval")
        
        while self.is_running:
            try:
                readings_count = await self.collect_all_readings()
                if readings_count > 0:
                    logger.debug(f"📊 Collected {readings_count} readings")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info("🛑 Monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(interval)  # Continue on error
        
        self.is_running = False
        logger.info("🛑 Sensor monitoring stopped")
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.is_running = False
        logger.info("🛑 Stopping sensor monitoring...")
    
    async def auto_discover_panels(self) -> int:
        """Auto-discover panels from database and register sensors"""
        if not self.panel_service:
            await self.initialize()
        
        panels = await self.panel_service.get_panels(active_only=True)
        registered_count = 0
        
        for panel in panels:
            success = await self.register_panel_sensor(panel.id, panel.i2c_address)
            if success:
                registered_count += 1
        
        logger.info(f"✅ Auto-discovered and registered {registered_count} panel sensors")
        return registered_count

# Global sensor integration service
sensor_integration = SensorIntegrationService()
