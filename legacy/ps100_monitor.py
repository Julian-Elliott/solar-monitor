#!/usr/bin/env python3
"""
PS100 Solar Monitor - Main Application
Real-time monitoring for Anker SOLIX PS100 solar panels

Features:
- Multi-panel support (up to 8 panels)
- Real-time data logging
- Performance analytics
- Alert system
- Web dashboard ready
"""

import asyncio
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import json
import board
import yaml
from pathlib import Path

from ps100_sensor_config import PS100SensorConfig
from ps100_database import PS100Database

class PS100Monitor:
    """Main solar monitoring application for PS100 panels"""
    
    def __init__(self, config_file: str = "config/panel_specifications.yaml"):
        """Initialize the PS100 monitoring system"""
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ps100_monitor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Initialize database
        self.db = PS100Database()
        
        # Initialize sensors
        self.sensors: Dict[str, PS100SensorConfig] = {}
        self.panels: List[Dict] = []
        
        # Control flags
        self.running = False
        self.monitoring_task = None
        
        # Statistics
        self.stats = {
            'readings_count': 0,
            'start_time': None,
            'last_reading_time': None,
            'errors': 0,
            'alerts': 0
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            config_path = Path(config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                self.logger.info(f"✅ Loaded configuration from {config_file}")
                return config
            else:
                self.logger.warning(f"⚠️  Config file {config_file} not found, using defaults")
                return self._get_default_config()
                
        except Exception as e:
            self.logger.error(f"❌ Failed to load config: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict:
        """Get default configuration for PS100 monitoring"""
        return {
            'panel_specs': {
                'model': 'Anker SOLIX PS100',
                'electrical': {
                    'peak_power': 100,
                    'rated_voltage_vmp': 26.5,
                    'rated_current_imp': 3.77,
                    'max_current_fused': 10.0
                }
            },
            'monitoring': {
                'sample_rate': 2,
                'data_retention': 365,
                'alert_thresholds': {
                    'min_voltage': 18.0,
                    'max_voltage': 25.0,
                    'max_current': 9.5,
                    'min_power_efficiency': 0.75,
                    'max_temperature': 70.0
                }
            },
            'system': {
                'max_panels': 8,
                'i2c_addresses': ['0x40', '0x41', '0x42', '0x43']
            }
        }
        
    async def initialize_sensors(self):
        """Initialize I2C sensors for all configured panels"""
        self.logger.info("🔧 Initializing PS100 sensors...")
        
        try:
            i2c = board.I2C()
            
            # Get configured I2C addresses
            addresses = self.config.get('system', {}).get('i2c_addresses', ['0x40'])
            
            for addr in addresses:
                try:
                    # Convert address to string and int
                    if isinstance(addr, int):
                        # YAML parsed hex as int, convert back to hex string and int
                        addr_str = f"0x{addr:02X}"
                        address = addr
                    elif isinstance(addr, str):
                        # Address is already a string
                        addr_str = addr
                        if addr_str.startswith('0x'):
                            address = int(addr_str, 16)
                        else:
                            address = int(addr_str)
                    else:
                        continue
                        
                    # Try to initialize sensor
                    sensor = PS100SensorConfig(i2c, address)
                    panel_id = f"PS100_{addr_str.upper()}"
                    
                    self.sensors[panel_id] = sensor
                    
                    # Add panel to database if not exists
                    self.db.add_panel(
                        panel_id=panel_id,
                        location=f"Sensor_{addr_str}",
                        sensor_address=addr_str,
                        notes=f"Auto-detected PS100 at {addr_str}"
                    )
                    
                    self.panels.append({
                        'id': panel_id,
                        'address': address,
                        'sensor': sensor,
                        'last_reading': None,
                        'error_count': 0
                    })
                    
                    self.logger.info(f"✅ Initialized sensor at {addr_str} -> {panel_id}")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️  Failed to initialize sensor at {addr_str}: {e}")
                    continue
                    
            if not self.sensors:
                raise Exception("No sensors initialized successfully")
                
            self.logger.info(f"✅ Initialized {len(self.sensors)} PS100 sensors")
            
            # Log startup event
            self.db.log_event(
                event_type="startup",
                message=f"PS100 Monitor started with {len(self.sensors)} panels",
                severity="info",
                details={'panel_count': len(self.sensors), 'panel_ids': list(self.sensors.keys())}
            )
            
        except Exception as e:
            self.logger.error(f"❌ Sensor initialization failed: {e}")
            raise
            
    async def read_all_panels(self) -> Dict[str, Dict]:
        """Read data from all panels concurrently"""
        readings = {}
        
        for panel in self.panels:
            try:
                # Read sensor data
                data = panel['sensor'].read_panel_data()
                
                # Validate readings
                issues = panel['sensor'].validate_readings(data)
                
                # Estimate conditions
                conditions = panel['sensor'].estimate_conditions(data)
                
                # Store reading with metadata
                reading = {
                    **data,
                    'panel_id': panel['id'],
                    'conditions': conditions,
                    'issues': issues,
                    'timestamp': datetime.now()
                }
                
                readings[panel['id']] = reading
                panel['last_reading'] = reading
                panel['error_count'] = 0  # Reset error count on successful read
                
                # Log to database
                self.db.log_reading(
                    panel_id=panel['id'],
                    voltage=data['voltage'],
                    current=data['current'],
                    power=data['power'],
                    temperature=data['temperature'],
                    energy=data['energy'],
                    alert_flags=data['alerts'],
                    conditions=conditions
                )
                
                # Check for alerts
                if any(data['alerts'].values()) or issues:
                    self.stats['alerts'] += 1
                    self._handle_alerts(panel['id'], data['alerts'], issues)
                    
            except Exception as e:
                panel['error_count'] += 1
                self.stats['errors'] += 1
                self.logger.error(f"❌ Failed to read {panel['id']}: {e}")
                
                # Log error event if persistent
                if panel['error_count'] >= 3:
                    self.db.log_event(
                        event_type="error",
                        message=f"Persistent read errors for {panel['id']}",
                        panel_id=panel['id'],
                        severity="warning",
                        details={'error_count': panel['error_count'], 'error': str(e)}
                    )
                    
        return readings
        
    def _handle_alerts(self, panel_id: str, alerts: Dict, issues: List[str]):
        """Handle panel alerts and validation issues"""
        
        # Log active alerts
        active_alerts = [flag for flag, status in alerts.items() if status]
        if active_alerts:
            self.logger.warning(f"🚨 ALERTS for {panel_id}: {', '.join(active_alerts)}")
            self.db.log_event(
                event_type="alert",
                message=f"Sensor alerts: {', '.join(active_alerts)}",
                panel_id=panel_id,
                severity="warning",
                details={'alerts': active_alerts}
            )
            
        # Log validation issues
        if issues:
            self.logger.warning(f"⚠️  ISSUES for {panel_id}: {'; '.join(issues)}")
            self.db.log_event(
                event_type="alert",
                message=f"Validation issues: {'; '.join(issues)}",
                panel_id=panel_id,
                severity="warning",
                details={'issues': issues}
            )
            
    def display_readings(self, readings: Dict[str, Dict]):
        """Display current readings in a formatted way"""
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'='*80}")
        print(f"🌞 PS100 Solar Monitor - {timestamp}")
        print(f"{'='*80}")
        
        if not readings:
            print("No readings available")
            return
            
        # System totals
        total_power = sum(r['power'] for r in readings.values())
        total_current = sum(r['current'] for r in readings.values())
        avg_voltage = sum(r['voltage'] for r in readings.values()) / len(readings)
        
        print(f"📊 SYSTEM TOTALS:")
        print(f"   Total Power: {total_power:6.1f}W")
        print(f"   Total Current: {total_current:5.1f}A")
        print(f"   Avg Voltage: {avg_voltage:5.1f}V")
        print(f"   Active Panels: {len(readings)}")
        
        print(f"\n📋 INDIVIDUAL PANELS:")
        
        for panel_id, reading in readings.items():
            status_icon = "✅" if not reading.get('issues') and not any(reading['alerts'].values()) else "⚠️"
            
            print(f"   {status_icon} {panel_id}:")
            print(f"      V: {reading['voltage']:5.1f}V  |  I: {reading['current']:5.2f}A  |  P: {reading['power']:6.1f}W")
            print(f"      Temp: {reading['temperature']:4.1f}°C  |  Conditions: {reading['conditions']}")
            
            if reading.get('issues'):
                print(f"      Issues: {'; '.join(reading['issues'])}")
                
        # Display statistics
        uptime = (datetime.now() - self.stats['start_time']).total_seconds() / 3600 if self.stats['start_time'] else 0
        print(f"\n📈 STATISTICS:")
        print(f"   Uptime: {uptime:.1f}h  |  Readings: {self.stats['readings_count']}  |  Errors: {self.stats['errors']}  |  Alerts: {self.stats['alerts']}")
        
    async def monitoring_loop(self):
        """Main monitoring loop"""
        sample_rate = self.config.get('monitoring', {}).get('sample_rate', 2)
        
        self.logger.info(f"🔄 Starting monitoring loop (sample rate: {sample_rate}s)")
        self.stats['start_time'] = datetime.now()
        
        while self.running:
            try:
                # Read all panels
                readings = await self.read_all_panels()
                
                # Update statistics
                self.stats['readings_count'] += len(readings)
                self.stats['last_reading_time'] = datetime.now()
                
                # Display readings
                self.display_readings(readings)
                
                # Wait for next sample
                await asyncio.sleep(sample_rate)
                
            except Exception as e:
                self.logger.error(f"❌ Monitoring loop error: {e}")
                await asyncio.sleep(sample_rate)
                
    async def start(self):
        """Start the monitoring system"""
        self.logger.info("🚀 Starting PS100 Solar Monitor...")
        
        try:
            # Initialize sensors
            await self.initialize_sensors()
            
            # Start monitoring
            self.running = True
            self.monitoring_task = asyncio.create_task(self.monitoring_loop())
            
            self.logger.info("✅ PS100 Monitor started successfully")
            print("\n🌞 PS100 Solar Monitor Running")
            print("Press Ctrl+C to stop...")
            
            # Wait for monitoring task
            await self.monitoring_task
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start monitor: {e}")
            await self.stop()
            raise
            
    async def stop(self):
        """Stop the monitoring system gracefully"""
        self.logger.info("🛑 Stopping PS100 Solar Monitor...")
        
        self.running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
                
        # Log shutdown event
        if hasattr(self, 'db'):
            uptime = (datetime.now() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
            
            self.db.log_event(
                event_type="shutdown",
                message="PS100 Monitor stopped",
                severity="info", 
                details={
                    'uptime_hours': round(uptime / 3600, 2),
                    'total_readings': self.stats['readings_count'],
                    'errors': self.stats['errors'],
                    'alerts': self.stats['alerts']
                }
            )
            
            self.db.close()
            
        self.logger.info("✅ PS100 Monitor stopped")
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"📡 Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.stop())

async def main():
    """Main entry point"""
    monitor = PS100Monitor()
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutdown requested by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
    finally:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())
