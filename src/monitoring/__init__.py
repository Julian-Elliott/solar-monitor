"""
PS100 Monitoring System
Main monitoring loop and coordination
"""

import time
import asyncio
import logging
from typing import Dict, Any, List

from ..sensors import PS100Sensor
from ..database import PS100Database


class PS100Monitor:
    """PS100 monitoring system with TimescaleDB"""
    
    def __init__(self, addresses: List[int] = None):
        self.addresses = addresses or [0x40]
        self.sensors = {}
        self.database = None
        self.running = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self._setup_components()
    
    def _setup_components(self):
        """Initialize sensors and database"""
        # Initialize sensors
        for addr in self.addresses:
            try:
                sensor = PS100Sensor(addr)
                panel_id = f'PS100_0X{addr:02X}'
                self.sensors[panel_id] = sensor
                self.logger.info(f"✅ Sensor {panel_id} ready")
            except Exception as e:
                self.logger.error(f"❌ Failed to init sensor at 0x{addr:02X}: {e}")
        
        if not self.sensors:
            raise RuntimeError("No sensors initialized successfully")
        
        # Initialize TimescaleDB
        self.database = PS100Database()
        self.logger.info("✅ Database (TimescaleDB) ready")
    
    async def run_monitor(self, read_interval: float = 1.0):
        """Main monitoring loop"""
        self.running = True
        self.logger.info(f"🚀 PS100 Monitor started - {len(self.sensors)} panels")
        
        try:
            while self.running:
                start_time = time.time()
                
                # Read all sensors
                for panel_id, sensor in self.sensors.items():
                    reading = sensor.read()
                    if reading:
                        self.database.store_reading(reading)
                        
                        # Log significant changes
                        if reading['power'] > 5 or reading['has_alerts']:
                            self.logger.info(
                                f"📊 {panel_id}: {reading['power']:.1f}W "
                                f"({reading['voltage']:.1f}V × {reading['current']:.2f}A) "
                                f"- {reading['conditions']}"
                            )
                
                # Sleep for remaining interval
                elapsed = time.time() - start_time
                sleep_time = max(0, read_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Monitor stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Monitor error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring and cleanup"""
        self.running = False
        if self.database:
            self.database.close()
        self.logger.info("✅ PS100 Monitor stopped")
    
    def status(self) -> Dict[str, Any]:
        """Get current system status"""
        recent = self.database.get_recent_readings(1)
        latest = recent[0] if recent else None
        
        return {
            'sensors': len(self.sensors),
            'database': "TimescaleDB",
            'latest_reading': latest,
            'running': self.running
        }
