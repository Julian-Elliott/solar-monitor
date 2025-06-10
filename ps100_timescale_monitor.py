#!/usr/bin/env python3
"""
PS100 Solar Monitor with TimescaleDB Integration
Real-time monitoring for Anker SOLIX PS100 solar panels with 1-second averaged permanent data storage

Features:
- Multi-panel PS100 support
- TimescaleDB with 1-second averaged data
- Real-time monitoring with high-frequency sampling
- Permanent data retention with compression
- Continuous aggregation for analytics
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
from ps100_timescaledb import PS100TimescaleDB

class PS100TimescaleMonitor:
    """PS100 solar monitoring with TimescaleDB integration"""
    
    def __init__(self, config_file: str = "config/panel_specifications.yaml"):
        """Initialize the PS100 monitoring system with TimescaleDB"""
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ps100_timescale_monitor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Initialize TimescaleDB
        self.db = PS100TimescaleDB()
        
        # Initialize sensors
        self.sensors: Dict[str, PS100SensorConfig] = {}
        self.panels: List[Dict] = []
        
        # Control flags
        self.running = False
        self.monitoring_task = None
        
        # High-frequency sampling configuration
        self.sample_interval = 0.1  # 100ms = 10Hz sampling
        self.display_interval = 5.0  # Update display every 5 seconds
        
        # Statistics
        self.stats = {
            'readings_count': 0,
            'start_time': None,
            'last_reading_time': None,
            'errors': 0,
            'alerts': 0,
            'database_writes': 0
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
                'sample_rate': 0.1,  # High frequency for TimescaleDB
                'display_rate': 5.0,
                'data_retention': 'permanent',
                'alert_thresholds': {
                    'min_voltage': 18.0,
                    'max_voltage': 28.0,
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
        self.logger.info("🔧 Initializing PS100 sensors for TimescaleDB monitoring...")
        
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
                    
                    # Add panel to TimescaleDB
                    self.db.add_panel(
                        panel_id=panel_id,
                        location=f"Sensor_{addr_str}",
                        sensor_address=addr_str,
                        notes=f"Auto-detected PS100 at {addr_str} for TimescaleDB monitoring"
                    )
                    
                    self.panels.append({
                        'id': panel_id,
                        'address': address,
                        'sensor': sensor,
                        'last_reading': None,
                        'error_count': 0,
                        'reading_count': 0
                    })
                    
                    self.logger.info(f"✅ Initialized sensor at {addr_str} -> {panel_id}")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️  Failed to initialize sensor at {addr_str}: {e}")
                    continue
                    
            if not self.sensors:
                raise Exception("No sensors initialized successfully")
                
            self.logger.info(f"✅ Initialized {len(self.sensors)} PS100 sensors for TimescaleDB")
            
            # Log startup event
            self.db.log_event(
                event_type="startup",
                message=f"PS100 TimescaleDB Monitor started with {len(self.sensors)} panels",
                severity="info",
                details={
                    'panel_count': len(self.sensors), 
                    'panel_ids': list(self.sensors.keys()),
                    'sample_rate': self.sample_interval,
                    'database': 'TimescaleDB'
                }
            )
            
        except Exception as e:
            self.logger.error(f"❌ Sensor initialization failed: {e}")
            raise
            
    async def read_all_panels(self) -> Dict[str, Dict]:
        """Read data from all panels and buffer to TimescaleDB"""
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
                panel['reading_count'] += 1
                
                # Buffer reading to TimescaleDB (will be averaged per second)
                self.db.buffer_reading(
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
                if panel['error_count'] >= 5:  # More tolerance for high-frequency sampling
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
        
        # Log active alerts to TimescaleDB
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
        """Display current readings and TimescaleDB statistics"""
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'='*90}")
        print(f"🌞 PS100 TimescaleDB Monitor - {timestamp}")
        print(f"{'='*90}")
        
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
        
        print(f"\n📋 INDIVIDUAL PANELS (High-Frequency Sampling):")
        
        for panel_id, reading in readings.items():
            status_icon = "✅" if not reading.get('issues') and not any(reading['alerts'].values()) else "⚠️"
            
            # Find panel stats
            panel_info = next((p for p in self.panels if p['id'] == panel_id), {})
            reading_count = panel_info.get('reading_count', 0)
            
            print(f"   {status_icon} {panel_id}:")
            print(f"      V: {reading['voltage']:5.1f}V  |  I: {reading['current']:5.2f}A  |  P: {reading['power']:6.1f}W")
            print(f"      Temp: {reading['temperature']:4.1f}°C  |  Conditions: {reading['conditions']}")
            print(f"      Readings: {reading_count} (buffered for 1s avg)")
            
            if reading.get('issues'):
                print(f"      Issues: {'; '.join(reading['issues'])}")
                
        # Display statistics and TimescaleDB info
        uptime = (datetime.now() - self.stats['start_time']).total_seconds() / 3600 if self.stats['start_time'] else 0
        sample_rate_actual = self.stats['readings_count'] / (uptime * 3600) if uptime > 0 else 0
        
        print(f"\n📈 PERFORMANCE STATISTICS:")
        print(f"   Uptime: {uptime:.1f}h  |  Total Readings: {self.stats['readings_count']:,}")
        print(f"   Sample Rate: {sample_rate_actual:.1f} Hz  |  Target: {1/self.sample_interval:.1f} Hz")
        print(f"   Errors: {self.stats['errors']}  |  Alerts: {self.stats['alerts']}")
        print(f"   🗄️  Database: TimescaleDB (1-second averaged, permanent retention)")
        
    async def monitoring_loop(self):
        """Main high-frequency monitoring loop with TimescaleDB integration"""
        
        self.logger.info(f"🔄 Starting high-frequency monitoring loop ({1/self.sample_interval:.1f} Hz -> TimescaleDB)")
        self.stats['start_time'] = datetime.now()
        
        last_display = time.time()
        latest_readings = {}
        
        while self.running:
            try:
                loop_start = time.time()
                
                # Read all panels at high frequency
                readings = await self.read_all_panels()
                latest_readings.update(readings)
                
                # Update statistics
                self.stats['readings_count'] += len(readings)
                self.stats['last_reading_time'] = datetime.now()
                
                # Display readings periodically (not every sample)
                if time.time() - last_display >= self.display_interval:
                    self.display_readings(latest_readings)
                    last_display = time.time()
                
                # Calculate sleep time to maintain target sample rate
                loop_duration = time.time() - loop_start
                sleep_time = max(0, self.sample_interval - loop_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    self.logger.warning(f"⚠️  Sampling too slow: {loop_duration:.3f}s > {self.sample_interval:.3f}s target")
                
            except Exception as e:
                self.logger.error(f"❌ Monitoring loop error: {e}")
                await asyncio.sleep(self.sample_interval)
                
    async def start(self):
        """Start the PS100 TimescaleDB monitoring system"""
        self.logger.info("🚀 Starting PS100 TimescaleDB Monitor...")
        
        try:
            # Initialize sensors
            await self.initialize_sensors()
            
            # Start monitoring
            self.running = True
            self.monitoring_task = asyncio.create_task(self.monitoring_loop())
            
            self.logger.info("✅ PS100 TimescaleDB Monitor started successfully")
            print(f"\n🌞 PS100 TimescaleDB Monitor Running")
            print(f"📊 High-frequency sampling: {1/self.sample_interval:.1f} Hz")
            print(f"🗄️  Database: TimescaleDB (1-second averaged)")
            print(f"💾 Data retention: Permanent")
            print("Press Ctrl+C to stop...")
            
            # Wait for monitoring task
            await self.monitoring_task
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start monitor: {e}")
            await self.stop()
            raise
            
    async def stop(self):
        """Stop the monitoring system gracefully"""
        self.logger.info("🛑 Stopping PS100 TimescaleDB Monitor...")
        
        self.running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
                
        # Flush any remaining data to TimescaleDB
        if hasattr(self, 'db'):
            self.logger.info("💾 Flushing final data to TimescaleDB...")
            self.db.force_flush()
            
            # Log shutdown event
            uptime = (datetime.now() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
            
            self.db.log_event(
                event_type="shutdown",
                message="PS100 TimescaleDB Monitor stopped",
                severity="info", 
                details={
                    'uptime_hours': round(uptime / 3600, 2),
                    'total_readings': self.stats['readings_count'],
                    'sample_rate_avg': self.stats['readings_count'] / uptime if uptime > 0 else 0,
                    'errors': self.stats['errors'],
                    'alerts': self.stats['alerts']
                }
            )
            
            self.db.close()
            
        self.logger.info("✅ PS100 TimescaleDB Monitor stopped")
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
        # Create new event loop for shutdown if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.stop())
            else:
                asyncio.run(self.stop())
        except:
            # If async doesn't work, at least flush the data
            if hasattr(self, 'db'):
                self.db.force_flush()
                self.db.close()

async def main():
    """Main entry point"""
    monitor = PS100TimescaleMonitor()
    
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
