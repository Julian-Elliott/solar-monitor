# 🌞 SolarScope Pro - Professional Solar Monitoring Platform

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-2.14+-orange.svg)](https://timescale.com)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://python.org)

A production-ready solar panel monitoring system for Anker SOLIX PS100 panels with real-time data collection, comprehensive analytics, and a professional REST API.

## ✨ Features

- 🔄 **Real-time Monitoring**: Continuous sensor data collection (voltage, current, power, temperature)
- 📊 **TimescaleDB Integration**: Optimized time-series data storage and analytics
- 🚀 **FastAPI Backend**: Modern async API with automatic documentation
- 🐳 **Docker Ready**: Complete containerized deployment
- 📱 **REST API**: Professional endpoints for integration and dashboards
- ⚡ **High Performance**: Async processing with background monitoring
- 🔒 **Production Security**: Health checks, proper error handling, logging
- 📈 **Scalable Architecture**: Microservices-ready design

## Project Structure

```
solar-monitor/
├── src/                    # Source modules (sensors, database, monitoring)
├── config/                 # Configuration files (.env, panel specs)
├── scripts/               # Utility scripts (start, test, setup)
├── docs/                  # Documentation
├── ps100_monitor.py       # Main entry point
└── requirements.txt       # Dependencies
```

## Quick Start

1. **Setup Environment**:
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your TimescaleDB settings
   ```

2. **Test System**:
   ```bash
   ./scripts/test/test_ps100_quick.sh
   ```

3. **Start Monitoring**:
   ```bash
   ./scripts/start_ps100.sh
   ```

## Usage

```bash
# Test mode
python3 ps100_monitor.py --test

# Continuous monitoring  
python3 ps100_monitor.py

# Multiple panels
python3 ps100_monitor.py --addresses 0x40 0x41
```

## Features

- TimescaleDB integration for time-series data
- Multi-panel support
- Real-time monitoring with configurable intervals
- Modular architecture (sensors, database, monitoring)
- Systemd service integration
- Comprehensive testing suite

## Requirements

- Python 3.8+
- TimescaleDB instance
- Raspberry Pi with I2C
- Adafruit INA228 sensor
- See requirements.txt for Python packages
