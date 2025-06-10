# PS100 Solar Monitor 🌞⚡

**Real-time monitoring system for Anker SOLIX PS100 solar panels**

This repository has been **completely rebuilt** and optimized specifically for **Anker SOLIX PS100** solar panels with TimescaleDB integration.

## 🎯 Quick Start

### For PS100 Solar Panel Monitoring:
👉 **See [README_PS100.md](README_PS100.md)** for complete setup instructions

### For TimescaleDB Integration:
👉 **See [PS100_TIMESCALEDB_SETUP.md](PS100_TIMESCALEDB_SETUP.md)** for TimescaleDB setup

## 🚀 Installation Options

### Option 1: SQLite Database (Standalone)
```bash
./setup_ps100.sh
sudo systemctl start ps100-monitor
```

### Option 2: TimescaleDB Integration (Recommended)
```bash
# Edit .env with TimescaleDB credentials
cp .env.example .env
nano .env

# Setup and start
./setup_ps100_timescale.sh
sudo systemctl start ps100-timescale-monitor
```

## ⚡ Anker SOLIX PS100 Specifications
- **Peak Power**: 100W
- **Operating Voltage**: 26.5V (Vmp)
- **Operating Current**: 3.77A (Imp)  
- **10A Fuse Protection**: Built-in safety
- **Multi-panel Support**: Up to 8 panels

## 📊 Features

✅ **Optimized for PS100**: Calibrated for 26.5V, 3.77A, 100W operation  
✅ **High-Frequency Sampling**: 10 Hz data collection with 1-second averaging  
✅ **TimescaleDB Integration**: Permanent data storage with compression  
✅ **Multi-Panel Support**: Monitor up to 8 PS100 panels individually  
✅ **Real-time Analytics**: Performance estimation and condition analysis  
✅ **Production Ready**: Systemd service with auto-restart  

## 📁 System Files

### Core Application
- `ps100_monitor.py` - Main monitoring application (SQLite)
- `ps100_timescale_monitor.py` - TimescaleDB monitoring application
- `ps100_sensor_config.py` - INA228 sensor configuration for PS100
- `ps100_database.py` - SQLite database layer
- `ps100_timescaledb.py` - TimescaleDB database layer

### Setup & Configuration
- `setup_ps100.sh` - SQLite setup script
- `setup_ps100_timescale.sh` - TimescaleDB setup script
- `config/panel_specifications.yaml` - PS100 configuration
- `.env.example` - Environment configuration template

### Documentation
- `README_PS100.md` - Complete PS100 setup guide
- `PS100_TIMESCALEDB_SETUP.md` - TimescaleDB integration guide
- `PS100_REBUILD_SUMMARY.md` - System rebuild documentation

## 🔧 Service Management

```bash
# SQLite version
sudo systemctl start ps100-monitor
sudo systemctl status ps100-monitor
sudo journalctl -u ps100-monitor -f

# TimescaleDB version  
sudo systemctl start ps100-timescale-monitor
sudo systemctl status ps100-timescale-monitor
sudo journalctl -u ps100-timescale-monitor -f
```

## 📈 Expected Output

```
🌞 PS100 Solar Monitor - 14:30:25
================================================================================
📊 SYSTEM TOTALS:
   Total Power:   245.3W
   Total Current:  9.2A
   Avg Voltage:   26.1V
   Active Panels: 3

📋 INDIVIDUAL PANELS:
   ✅ PS100_0X40: V: 26.3V | I: 3.65A | P: 96.0W | Excellent - Full sun
   ✅ PS100_0X41: V: 26.0V | I: 3.71A | P: 96.5W | Excellent - Full sun
   ⚠️ PS100_0X42: V: 25.8V | I: 2.05A | P: 52.8W | Good - Partial sun

📈 STATISTICS:
   Uptime: 2.3h | Readings: 4,147 | Errors: 0 | Alerts: 3
```

---

**Built specifically for Anker SOLIX PS100 Solar Panels** | **Multi-panel support** | **TimescaleDB integration** | **Production ready**

## Hardware Requirements
- Raspberry Pi (any model with GPIO)
- Adafruit INA228 I2C Power Monitor
- Solar panel and battery setup
- Network connection to TimescaleDB server

## Quick Setup on Raspberry Pi

### Prerequisites
1. **TimescaleDB server** running and accessible
2. **Database credentials** ready
3. **I2C enabled** on Raspberry Pi

### Automatic Setup
```bash
git clone https://github.com/julian-elliott/solar-monitor.git
cd solar-monitor
chmod +x setup.sh
./setup.sh
```

### Database Configuration
Create a `.env` file with your TimescaleDB credentials:
```bash
# Copy the example and edit with your values
cp .env.example .env
nano .env
```

Example `.env` content:
```
TIMESCALE_HOST=192.168.42.125
TIMESCALE_PORT=6543
TIMESCALE_USER=your-username
TIMESCALE_PASSWORD=your-password
TIMESCALE_DATABASE=solar_monitor
SENSOR_READ_INTERVAL=0.1
BATCH_INSERT_SIZE=10
```

### Start Data Logging
```bash
# Test the setup first
./start_logger.sh
```

### Manual Setup
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev

# Enable I2C interface
sudo raspi-config nonint do_i2c 0

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

## Usage

### 1. **Start Data Logging**
   ```bash
   ./start_logger.sh
   ```
   This will:
   - Activate the virtual environment
   - Test database connection
   - Start continuous sensor reading and data logging

### 2. **Test Sensor Connection**
   ```bash
   source .venv/bin/activate
   python3 test_sensor.py
   ```

### 3. **Query Logged Data**
   ```bash
   source .venv/bin/activate
   python3 query_data.py
   ```

### 4. **Database Setup/Test**
   ```bash
   source .venv/bin/activate
   python3 db_setup.py
   ```

## Data Schema

The system logs the following measurements to TimescaleDB:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | TIMESTAMPTZ | UTC timestamp of reading |
| `voltage` | DOUBLE PRECISION | Bus voltage (V) |
| `current` | DOUBLE PRECISION | Current (A) |
| `power` | DOUBLE PRECISION | Power (W) |
| `shunt_voltage` | DOUBLE PRECISION | Shunt voltage (V) |
| `temperature` | DOUBLE PRECISION | Die temperature (°C) |
| `energy` | DOUBLE PRECISION | Accumulated energy (J) |
| `charge` | DOUBLE PRECISION | Accumulated charge (C) |

## Performance

- **Sensor reading frequency**: Up to 10 Hz (100ms intervals)
- **Database batch size**: 10 readings per insert
- **Typical throughput**: ~600 readings/minute
- **Data retention**: Managed by TimescaleDB policies

## Project Structure
```
solar-monitor/
├── .venv/                          # Virtual environment
├── .env                           # Database configuration (not in git)
├── documentation/
│   └── sensor/
│       └── adafruit-ina228-i2c-power-monitor.pdf
├── requirements.txt               # Python dependencies
├── setup.sh                      # Automated setup script
├── start_logger.sh               # Start data logging
├── data_logger.py                # Main data logging application
├── db_setup.py                   # Database setup and testing
├── query_data.py                 # Query logged data
├── test_sensor.py                # Sensor testing
└── README.md                     # This file
```

## Scripts Description

- **`setup.sh`** - Initial system setup, installs dependencies
- **`start_logger.sh`** - Convenient startup script for data logging
- **`data_logger.py`** - High-performance data logger with TimescaleDB integration
- **`db_setup.py`** - Test database connection and create tables
- **`query_data.py`** - View recent data and statistics
- **`test_sensor.py`** - Basic sensor connectivity test

## Troubleshooting

### I2C Issues
- Ensure I2C is enabled: `sudo raspi-config` → Interface Options → I2C → Enable
- Check I2C devices: `sudo i2cdetect -y 1`
- Reboot after enabling I2C for the first time

### Database Connection Issues
- Verify TimescaleDB server is running and accessible
- Check network connectivity: `ping 192.168.42.125`
- Test database credentials with `python3 db_setup.py`
- Check firewall settings on TimescaleDB server

### Permission Issues
- Add user to i2c group: `sudo usermod -a -G i2c $USER`
- Logout and login again
- Ensure `.env` file has correct permissions: `chmod 600 .env`

### Virtual Environment
- Always activate before running: `source .venv/bin/activate`
- To deactivate: `deactivate`
- Reinstall if corrupted: `rm -rf .venv && ./setup.sh`

### Service Issues
- Check service status: `sudo systemctl status solar-monitor`
- View logs: `sudo journalctl -u solar-monitor -f`
- Restart service: `sudo systemctl restart solar-monitor`

## Running as a Service

To run the data logger automatically on boot:

```bash
# Install as a system service
./install_service.sh

# Start the service
sudo systemctl start solar-monitor

# View logs
sudo journalctl -u solar-monitor -f
```

## Performance Tuning

### High-Frequency Logging
For maximum data collection frequency, adjust in `.env`:
```
SENSOR_READ_INTERVAL=0.05  # 20 Hz
BATCH_INSERT_SIZE=20       # Larger batches
```

### Database Optimization
- Use TimescaleDB compression policies
- Set up data retention policies
- Consider partitioning by device_id for multiple sensors

## Documentation
- Sensor documentation: `documentation/sensor/`
- TimescaleDB docs: https://docs.timescale.com/
- INA228 datasheet: Available in documentation folder
