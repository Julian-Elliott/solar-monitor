# PS100 TimescaleDB Integration - Complete Setup

**Created: June 10, 2025**  
**TimescaleDB Integration for Anker SOLIX PS100 Solar Panels**

## 🎯 Overview

I've created a complete TimescaleDB integration for your PS100 solar monitoring system that provides:

- **High-frequency sampling** (10 Hz) with **1-second averaged permanent data storage**
- **TimescaleDB hypertables** optimized for time-series data
- **Continuous aggregation** for 5-minute, hourly, and daily summaries
- **Permanent data retention** with automatic compression
- **Multi-panel support** for up to 8 PS100 panels

## 📁 New Files Created

### Core TimescaleDB Integration
1. **`ps100_timescaledb.py`** - TimescaleDB database layer with PS100 optimization
2. **`ps100_timescale_monitor.py`** - Main monitoring application with TimescaleDB
3. **`setup_ps100_timescale.sh`** - Complete setup script for TimescaleDB integration

### Database Schema Features
- **`ps100_panels`** - Panel configuration (regular PostgreSQL table)
- **`ps100_readings_1s`** - 1-second averaged readings (TimescaleDB hypertable)
- **`ps100_system_1s`** - System-wide aggregates (TimescaleDB hypertable)
- **`ps100_events`** - Events and alerts log
- **Continuous Aggregates**: 5-minute, hourly, and daily views

## 🔧 Key Features

### 1. High-Performance Data Collection
```
Sample Rate: 10 Hz (100ms intervals)
Database Storage: 1-second averages (permanent)
Data Processing: Real-time buffering and aggregation
Compression: Automatic after 7 days
```

### 2. Optimized Database Schema
```sql
-- 1-second averaged readings with statistics
ps100_readings_1s (
    time TIMESTAMPTZ,
    panel_id TEXT,
    voltage_avg/min/max/stddev REAL,
    current_avg/min/max/stddev REAL,  
    power_avg/min/max/peak REAL,
    energy_wh REAL,                   -- Wh for this second
    temperature_avg/min/max REAL,
    sample_count INTEGER,             -- Samples in this second
    efficiency_percent REAL,
    conditions_estimate TEXT,
    alerts JSONB
)
```

### 3. Automatic Continuous Aggregation
- **5-minute aggregates**: `ps100_readings_5min`
- **Hourly aggregates**: `ps100_readings_1hour`  
- **Daily aggregates**: `ps100_readings_daily` (with kWh totals)

### 4. Data Quality and Performance Metrics
- **Sample count per second** (should be ~10 at 10Hz)
- **Voltage/current standard deviation** (data quality indicator)
- **Alert and error counting**
- **Performance efficiency calculations**

## 🚀 Setup Instructions

### 1. Configure Environment
```bash
# Edit .env with your TimescaleDB credentials
cp .env.example .env
nano .env
```

Required `.env` settings:
```bash
TIMESCALE_HOST=192.168.42.125
TIMESCALE_PORT=6543
TIMESCALE_USER=your-username
TIMESCALE_PASSWORD=your-password
TIMESCALE_DATABASE=solar_monitor
```

### 2. Install TimescaleDB Integration
```bash
# Run the TimescaleDB setup
./setup_ps100_timescale.sh

# Test the setup
./test_ps100_timescale.sh
```

### 3. Start Monitoring
```bash
# Manual start (for testing)
./start_ps100_timescale.sh

# Or install as service
sudo systemctl enable ps100-timescale-monitor
sudo systemctl start ps100-timescale-monitor
```

## 📊 Expected Performance

### High-Frequency Monitoring Output
```
🌞 PS100 TimescaleDB Monitor - 14:30:25
================================================================================
📊 SYSTEM TOTALS:
   Total Power:   245.3W
   Total Current:  9.2A
   Avg Voltage:   26.1V
   Active Panels: 3

📋 INDIVIDUAL PANELS (High-Frequency Sampling):
   ✅ PS100_0X40:
      V:  26.3V  |  I:  3.65A  |  P:   96.0W
      Temp: 28.5°C  |  Conditions: Excellent - Full sun
      Readings: 1,247 (buffered for 1s avg)

📈 PERFORMANCE STATISTICS:
   Uptime: 2.3h  |  Total Readings: 41,470
   Sample Rate: 10.0 Hz  |  Target: 10.0 Hz
   Errors: 0  |  Alerts: 3
   🗄️  Database: TimescaleDB (1-second averaged, permanent retention)
```

### Data Storage Characteristics
- **Raw samples**: 10 Hz per panel (86,400 samples/day/panel)
- **Stored data**: 1-second averages (86,400 records/day/panel)
- **Compression**: Automatic after 7 days
- **Retention**: Permanent (no automatic deletion)

## 🗄️ Database Queries

### Essential Queries

#### 1. Latest Panel Performance
```sql
SELECT 
    time,
    panel_id,
    voltage_avg,
    current_avg,
    power_avg,
    efficiency_percent,
    conditions_estimate
FROM ps100_readings_1s 
WHERE time > NOW() - INTERVAL '1 hour'
ORDER BY time DESC;
```

#### 2. Daily Energy Production
```sql
SELECT 
    panel_id,
    DATE(time) as date,
    SUM(energy_wh) / 1000.0 as daily_energy_kwh,
    AVG(power_avg) as avg_power,
    MAX(power_peak) as peak_power,
    AVG(efficiency_percent) as avg_efficiency
FROM ps100_readings_1s
WHERE time > NOW() - INTERVAL '7 days'
GROUP BY panel_id, DATE(time)
ORDER BY date DESC, panel_id;
```

#### 3. System Performance Trends
```sql
SELECT 
    DATE_TRUNC('hour', time) as hour,
    COUNT(DISTINCT panel_id) as active_panels,
    SUM(power_avg) as total_system_power,
    SUM(energy_wh) / 1000.0 as hourly_energy_kwh,
    AVG(efficiency_percent) as avg_efficiency
FROM ps100_readings_1s
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', time)
ORDER BY hour DESC;
```

### Fast Aggregate Queries
```sql
-- Use continuous aggregates for better performance over long periods

-- 5-minute data (last 24 hours)
SELECT * FROM ps100_readings_5min 
WHERE time > NOW() - INTERVAL '24 hours';

-- Hourly data (last week)
SELECT * FROM ps100_readings_1hour
WHERE time > NOW() - INTERVAL '7 days';

-- Daily data (last month)
SELECT * FROM ps100_readings_daily
WHERE time > NOW() - INTERVAL '30 days';
```

## 📈 Data Analysis Benefits

### 1. High Resolution Insights
- **Second-by-second performance** tracking
- **Cloud pass detection** (rapid power changes)
- **Panel mismatch identification** (performance differences)
- **Micro-shading analysis** (voltage/current patterns)

### 2. Statistical Analysis
- **Standard deviation metrics** for data quality assessment
- **Efficiency calculations** per panel and system-wide
- **Performance correlation** between panels
- **Environmental condition estimation**

### 3. Long-term Trends
- **Seasonal performance patterns**
- **Panel degradation detection** over time
- **Optimal performance time identification**
- **Energy production forecasting** data

## 🔧 Service Management

### Service Commands
```bash
# Start/stop TimescaleDB monitoring
sudo systemctl start ps100-timescale-monitor
sudo systemctl stop ps100-timescale-monitor

# Check status and logs
sudo systemctl status ps100-timescale-monitor
sudo journalctl -u ps100-timescale-monitor -f

# Enable auto-start
sudo systemctl enable ps100-timescale-monitor
```

### Log Files
- **Service logs**: `sudo journalctl -u ps100-timescale-monitor`
- **Application logs**: `ps100_timescale_monitor.log`
- **Database**: TimescaleDB at your configured host

## 🔍 Troubleshooting

### Common Issues

#### 1. TimescaleDB Connection
```bash
# Test connection
python3 -c "from ps100_timescaledb import PS100TimescaleDB; db = PS100TimescaleDB(); db.close()"

# Check environment variables
cat .env | grep TIMESCALE
```

#### 2. High CPU Usage
- **Expected**: 10 Hz sampling uses more CPU than 0.5 Hz
- **Optimization**: Reduce sample rate in `.env` if needed
- **Monitoring**: Watch `top` and `htop` for python3 process

#### 3. Data Quality Issues
```sql
-- Check sample counts (should be ~10 per second)
SELECT 
    panel_id,
    AVG(sample_count) as avg_samples_per_second,
    MIN(sample_count) as min_samples,
    MAX(sample_count) as max_samples
FROM ps100_readings_1s
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY panel_id;
```

## 📊 Performance Optimization

### For Maximum Performance
```bash
# In .env file
SENSOR_READ_INTERVAL=0.1    # 10 Hz (current)
# SENSOR_READ_INTERVAL=0.2  # 5 Hz (lighter load)
# SENSOR_READ_INTERVAL=0.5  # 2 Hz (minimal load)
```

### TimescaleDB Settings
- **Chunk interval**: 1 day (optimal for 1-second data)
- **Compression**: After 7 days (balance between query speed and storage)
- **Continuous aggregates**: Updated automatically

## 🎯 Summary

**✅ COMPLETE**: Your PS100 solar monitoring system now includes:

- **TimescaleDB Integration**: High-performance time-series database
- **1-Second Averaging**: Permanent data with statistical analysis
- **High-Frequency Sampling**: 10 Hz data collection for maximum insight
- **Continuous Aggregation**: Automatic 5min/hourly/daily summaries
- **Multi-Panel Support**: Up to 8 PS100 panels with individual tracking
- **Production Ready**: Systemd service with proper error handling

**Ready for high-performance, permanent data collection from your Anker SOLIX PS100 panels!**

### Next Steps
1. Configure your `.env` file with TimescaleDB credentials
2. Run `./setup_ps100_timescale.sh`
3. Test with `./test_ps100_timescale.sh`
4. Start monitoring: `sudo systemctl start ps100-timescale-monitor`
5. Query your data using the provided SQL examples

Your PS100 panels will now generate permanent, high-resolution data perfect for detailed solar performance analysis!
