# PS100 Solar Monitor

**Real-time monitoring system for Anker SOLIX PS100 solar panels**

*Updated: June 10, 2025*

## 🌞 Overview

This is a complete rebuild of the solar monitoring system, specifically optimized for **Anker SOLIX PS100** solar panels. The system provides real-time monitoring, data logging, analytics, and alerting for multiple PS100 panels.

### ⚡ Anker SOLIX PS100 Specifications
- **Peak Power**: 100W
- **Operating Voltage (Vmp)**: 26.5V  
- **Open Circuit Voltage (Voc)**: 24.5V
- **Operating Current (Imp)**: 3.77A
- **Short Circuit Current (Isc)**: 4.1A
- **Cell Type**: Monocrystalline (23% efficiency)
- **Fuse Protection**: 10A inline fuse (user configured)

## 🎯 Features

### ✅ Current Features (Phase 1)
- **Multi-Panel Support**: Monitor up to 8 PS100 panels simultaneously
- **Real-time Data Collection**: Voltage, current, power, temperature every 2 seconds
- **Optimized Sensor Configuration**: INA228 calibrated for PS100 specifications
- **SQLite Database**: Historical data storage with 365-day retention
- **Alert System**: Over/under voltage, current, temperature monitoring
- **Performance Analytics**: Efficiency calculations and condition estimation
- **Graceful Shutdown**: Signal handling and proper cleanup
- **Systemd Service**: Background monitoring with auto-restart

### 🚧 Planned Features
- **Phase 2**: Web dashboard with real-time charts
- **Phase 3**: Advanced analytics and trend analysis  
- **Phase 4**: Remote monitoring and mobile alerts

## 🔧 Hardware Requirements

### Required Components
- **Raspberry Pi 4B** (or newer) with Raspberry Pi OS
- **INA228 I2C Power Monitor** sensors (one per panel)
- **Anker SOLIX PS100** solar panels
- **10A inline fuses** (for protection)
- **MC4 connectors** and appropriate wiring
- **0.01Ω (10mΩ) shunt resistors** for current sensing

### I2C Address Configuration
The system supports up to 8 panels with sensors at addresses:
- `0x40` - Panel 1 (default)
- `0x41` - Panel 2  
- `0x42` - Panel 3
- `0x43` - Panel 4
- `0x44` - Panel 5
- `0x45` - Panel 6
- `0x46` - Panel 7
- `0x47` - Panel 8

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository>
cd solar-monitor
./setup_ps100.sh
```

### 2. Test Installation
```bash
./test_ps100_setup.sh
```

### 3. Start Monitoring
```bash
# Manual start (for testing)
./start_ps100_monitor.sh

# Or install as service
sudo systemctl enable ps100-monitor
sudo systemctl start ps100-monitor
```

## 📊 Monitoring Output

The system provides real-time console output showing:

```
================================================================================
🌞 PS100 Solar Monitor - 14:30:25
================================================================================
📊 SYSTEM TOTALS:
   Total Power:   245.3W
   Total Current:  9.2A
   Avg Voltage:   26.1V
   Active Panels: 3

📋 INDIVIDUAL PANELS:
   ✅ PS100_0X40:
      V:  26.3V  |  I:  3.65A  |  P:   96.0W
      Temp: 28.5°C  |  Conditions: Excellent - Full sun
   ✅ PS100_0X41:
      V:  26.0V  |  I:  3.71A  |  P:   96.5W
      Temp: 30.1°C  |  Conditions: Excellent - Full sun
   ⚠️ PS100_0X42:
      V:  25.8V  |  I:  2.05A  |  P:   52.8W
      Temp: 32.0°C  |  Conditions: Good - Partial sun
      Issues: Power below optimal for conditions

📈 STATISTICS:
   Uptime: 2.3h  |  Readings: 4,147  |  Errors: 0  |  Alerts: 3
```

## 🗄️ Database Schema

### Core Tables
- **`panels`**: Panel configuration and metadata
- **`panel_readings`**: Real-time sensor data (2-second intervals)
- **`panel_aggregates`**: Aggregated data (1min, 5min, 1hour, daily)
- **`system_aggregates`**: System-wide performance summaries
- **`system_events`**: Alerts, errors, and maintenance events

### Data Retention
- **Raw readings**: 365 days (configurable)
- **Aggregated data**: Permanent retention
- **Events/alerts**: Permanent retention

## ⚙️ Configuration

### Main Configuration File: `config/panel_specifications.yaml`

```yaml
# Panel specifications
panel_specs:
  model: "Anker SOLIX PS100"
  electrical:
    peak_power: 100
    rated_voltage_vmp: 26.5
    rated_current_imp: 3.77
    max_current_fused: 10.0

# Monitoring settings  
monitoring:
  sample_rate: 2  # seconds
  data_retention: 365  # days
  alert_thresholds:
    min_voltage: 18.0
    max_voltage: 25.0
    max_current: 9.5
    min_power_efficiency: 0.75

# System configuration
system:
  max_panels: 8
  i2c_addresses: ['0x40', '0x41', '0x42', '0x43']
```

## 🔧 Service Management

### Service Commands
```bash
# Start monitoring
sudo systemctl start ps100-monitor

# Stop monitoring  
sudo systemctl stop ps100-monitor

# Check status
sudo systemctl status ps100-monitor

# View logs
sudo journalctl -u ps100-monitor -f

# Enable auto-start
sudo systemctl enable ps100-monitor
```

### Log Files
- **Service logs**: `sudo journalctl -u ps100-monitor`
- **Application logs**: `ps100_monitor.log`
- **Database**: `ps100_solar.db`

## 🔍 Troubleshooting

### Common Issues

#### No Sensors Detected
```bash
# Check I2C is enabled
ls /dev/i2c-*

# Scan for I2C devices
i2cdetect -y 1

# Check permissions
sudo usermod -a -G i2c pi
```

#### Voltage Reading Issues
- Verify 10mΩ shunt resistor installation
- Check sensor calibration: `python3 ps100_sensor_config.py`
- Ensure proper grounding and connections

#### Database Errors
```bash
# Check database file permissions
ls -la ps100_solar.db

# Test database manually
python3 -c "from ps100_database import PS100Database; db = PS100Database(); db.close()"
```

### Performance Optimization

#### For Multiple Panels (4+)
- Increase I2C bus speed in `/boot/config.txt`:
  ```
  dtparam=i2c_arm=on,i2c_arm_baudrate=400000
  ```
- Consider using multiple I2C buses for >4 panels

#### Memory Usage
- Automatic cleanup of old readings (configurable retention)
- Database optimization with indexing
- Log rotation for service logs

## 📈 Performance Expectations

### Optimal Conditions (Full Sun)
- **Voltage**: 25.0-26.5V per panel
- **Current**: 3.5-3.8A per panel  
- **Power**: 90-100W per panel
- **Efficiency**: >90% of rated power

### Good Conditions (Partial Sun)
- **Voltage**: 22.0-26.0V per panel
- **Current**: 2.0-3.5A per panel
- **Power**: 50-90W per panel
- **Efficiency**: 50-90% of rated power

### Alert Thresholds
- **Voltage**: <18V or >28V
- **Current**: >9.5A (fuse protection)
- **Temperature**: >70°C (sensor protection)
- **Power**: <75% expected for conditions

## 🛠️ Development

### Project Structure
```
solar-monitor/
├── ps100_monitor.py           # Main application
├── ps100_sensor_config.py     # INA228 configuration for PS100
├── ps100_database.py          # Database management
├── config/
│   └── panel_specifications.yaml
├── logs/
├── data/
└── requirements.txt
```

### Adding New Features
1. **Sensor modifications**: Update `ps100_sensor_config.py`
2. **Database schema**: Modify `ps100_database.py`
3. **Configuration**: Update YAML schema
4. **Main logic**: Extend `ps100_monitor.py`

### Testing
```bash
# Test sensor configuration
python3 ps100_sensor_config.py

# Test database
python3 ps100_database.py

# Full system test  
./test_ps100_setup.sh
```

## 📋 Migration from Old System

The previous system had several issues:
- ❌ **Scale mismatch**: Designed for milliwatts, PS100 produces 100W
- ❌ **Poor calibration**: 0.004V readings instead of 26.5V
- ❌ **Single panel**: No multi-panel architecture
- ❌ **Inadequate range**: Current handling insufficient for 10A

### New System Improvements
- ✅ **Proper scaling**: Designed for 100W PS100 panels
- ✅ **Accurate calibration**: 26.5V / 3.77A specifications
- ✅ **Multi-panel support**: Up to 8 panels with individual monitoring
- ✅ **10A fuse protection**: Safety-first design
- ✅ **Modern architecture**: Async, database, web-ready

## 📞 Support

### Logs to Check
1. **Service status**: `sudo systemctl status ps100-monitor`
2. **Application logs**: `tail -f ps100_monitor.log`
3. **System logs**: `sudo journalctl -u ps100-monitor -f`
4. **I2C connectivity**: `i2cdetect -y 1`

### Common Solutions
- **Restart service**: `sudo systemctl restart ps100-monitor`
- **Reboot system**: `sudo reboot` (if I2C issues)
- **Reinstall**: Re-run `./setup_ps100.sh`

---

**Built for Anker SOLIX PS100 Solar Panels** | **Real-time monitoring** | **Multi-panel support** | **10A fuse protection**
