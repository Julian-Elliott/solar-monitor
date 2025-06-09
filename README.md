# Solar Monitor 🌞⚡

A high-performance Raspberry Pi-based solar power monitoring system using the Adafruit INA228 I2C power monitor with TimescaleDB data storage.

## Features
- **High-frequency data collection** (up to 10 Hz sensor readings)
- **TimescaleDB integration** for time-series data storage
- **Real-time monitoring** with continuous data logging
- **Batch data insertion** for optimal database performance
- **Automatic reconnection** and error recovery
- **Comprehensive logging** and monitoring

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
