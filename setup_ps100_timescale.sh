#!/bin/bash
# PS100 TimescaleDB Setup Script
# Updated: June 10, 2025
# Sets up Anker SOLIX PS100 monitoring with TimescaleDB integration

set -e

echo "🌞 PS100 TimescaleDB Monitor Setup"
echo "=================================="
echo "Setting up monitoring for Anker SOLIX PS100 solar panels with TimescaleDB"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   ✅ Created .env file from .env.example"
        echo "   ⚠️  Please edit .env with your TimescaleDB credentials!"
        echo ""
    else
        echo "❌ No .env.example file found. Creating basic template..."
        cat > .env << 'EOF'
# TimescaleDB Configuration for PS100 Monitoring
TIMESCALE_HOST=192.168.42.125
TIMESCALE_PORT=6543
TIMESCALE_USER=your-username
TIMESCALE_PASSWORD=your-password
TIMESCALE_DATABASE=solar_monitor

# PS100 Monitoring Configuration
SENSOR_READ_INTERVAL=0.1  # 100ms = 10Hz sampling
BATCH_INSERT_SIZE=10      # Readings per batch
LOG_LEVEL=INFO
EOF
        echo "   ✅ Created basic .env template"
        echo "   ⚠️  IMPORTANT: Edit .env with your actual TimescaleDB credentials!"
        echo ""
    fi
else
    echo "📄 Using existing .env file"
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $PYTHON_VERSION"

if [ "$(printf '%s\n' "$PYTHON_VERSION" "3.8" | sort -V | head -n1)" != "3.8" ]; then
    echo "❌ Python 3.8+ required, found $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
echo "📦 Setting up virtual environment..."
if [ -d "venv" ]; then
    echo "   Virtual environment already exists"
else
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install TimescaleDB specific dependencies
echo "📚 Installing TimescaleDB dependencies..."
pip install psycopg2-binary>=2.9.0
pip install python-dotenv>=1.0.0
pip install numpy>=1.21.0

# Install other requirements
echo "📦 Installing remaining dependencies..."
pip install -r requirements.txt

# Test TimescaleDB connection
echo "🔍 Testing TimescaleDB connection..."
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Test environment variables
required_vars = ['TIMESCALE_HOST', 'TIMESCALE_PORT', 'TIMESCALE_USER', 'TIMESCALE_PASSWORD', 'TIMESCALE_DATABASE']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f'❌ Missing environment variables: {missing_vars}')
    print('   Please edit .env file with your TimescaleDB credentials')
    exit(1)

print('✅ Environment variables configured')
print(f'   Host: {os.getenv(\"TIMESCALE_HOST\")}:{os.getenv(\"TIMESCALE_PORT\")}')
print(f'   Database: {os.getenv(\"TIMESCALE_DATABASE\")}')
print(f'   User: {os.getenv(\"TIMESCALE_USER\")}')
"

# Test TimescaleDB schema creation
echo "🗄️  Testing TimescaleDB schema creation..."
python3 -c "
try:
    from ps100_timescaledb import PS100TimescaleDB
    print('📊 Testing TimescaleDB connection and schema...')
    db = PS100TimescaleDB()
    print('✅ TimescaleDB connection successful')
    print('✅ PS100 schema created/verified')
    db.close()
except Exception as e:
    print(f'❌ TimescaleDB test failed: {e}')
    print('   Check your .env file and TimescaleDB server')
    exit(1)
"

# Test sensor modules
echo "🧪 Testing PS100 sensor modules..."
python3 -c "
try:
    from ps100_sensor_config import PS100SensorConfig
    print('✅ PS100 sensor configuration module loaded')
except ImportError as e:
    print(f'❌ Failed to load PS100 sensor module: {e}')
    exit(1)
except Exception as e:
    print(f'⚠️  Sensor module loaded but hardware test failed: {e}')
    print('   This is normal if no hardware is connected')
"

# Create TimescaleDB systemd service
echo "⚙️  Creating TimescaleDB systemd service..."
SERVICE_FILE="/etc/systemd/system/ps100-timescale-monitor.service"

sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=PS100 Solar Panel Monitor with TimescaleDB
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$(pwd)/venv/bin/python3 $(pwd)/ps100_timescale_monitor.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment file
EnvironmentFile=$(pwd)/.env

# Resource limits
LimitNOFILE=65536
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$(pwd)

[Install]
WantedBy=multi-user.target
EOF

echo "   ✅ Service file created: $SERVICE_FILE"

# Reload systemd
sudo systemctl daemon-reload

# Create TimescaleDB startup script
echo "🚀 Creating TimescaleDB startup script..."
cat > start_ps100_timescale.sh << 'EOF'
#!/bin/bash
# PS100 TimescaleDB Monitor Startup Script

cd "$(dirname "$0")"

echo "🌞 Starting PS100 TimescaleDB Monitor..."

# Load environment variables
source .env

# Activate virtual environment
source venv/bin/activate

# Check TimescaleDB connection
echo "🔍 Testing TimescaleDB connection..."
python3 -c "
from ps100_timescaledb import PS100TimescaleDB
try:
    db = PS100TimescaleDB()
    print('✅ TimescaleDB connection OK')
    db.close()
except Exception as e:
    print(f'❌ TimescaleDB connection failed: {e}')
    exit(1)
"

# Check if service is running
if systemctl is-active --quiet ps100-timescale-monitor; then
    echo "📋 Service is already running"
    echo "   Status: sudo systemctl status ps100-timescale-monitor"
    echo "   Logs: sudo journalctl -u ps100-timescale-monitor -f"
else
    echo "🔄 Starting PS100 TimescaleDB monitor..."
    python3 ps100_timescale_monitor.py
fi
EOF

chmod +x start_ps100_timescale.sh

# Create TimescaleDB test script
echo "🧪 Creating TimescaleDB test script..."
cat > test_ps100_timescale.sh << 'EOF'
#!/bin/bash
# Test PS100 TimescaleDB Setup

cd "$(dirname "$0")"
source venv/bin/activate

echo "🔍 PS100 TimescaleDB Setup Test"
echo "==============================="

# Test 1: Environment variables
echo "1. Environment Variables:"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['TIMESCALE_HOST', 'TIMESCALE_PORT', 'TIMESCALE_USER', 'TIMESCALE_PASSWORD', 'TIMESCALE_DATABASE']
for var in required:
    value = os.getenv(var)
    if value:
        if 'PASSWORD' in var:
            print(f'   {var}: ***hidden***')
        else:
            print(f'   {var}: {value}')
    else:
        print(f'   ❌ {var}: Not set')
"

# Test 2: TimescaleDB Connection
echo "2. TimescaleDB Connection:"
python3 -c "
from ps100_timescaledb import PS100TimescaleDB
try:
    db = PS100TimescaleDB()
    print('   ✅ Connection successful')
    
    # Test adding a panel
    db.add_panel('TEST_PANEL', 'Test Location', '0x40')
    print('   ✅ Panel creation test passed')
    
    # Test data buffering
    db.buffer_reading('TEST_PANEL', 25.0, 3.5, 87.5, 30.0)
    print('   ✅ Data buffering test passed')
    
    db.close()
except Exception as e:
    print(f'   ❌ TimescaleDB test failed: {e}')
"

# Test 3: Sensor Configuration
echo "3. Sensor Configuration:"
python3 -c "
from ps100_sensor_config import PS100SensorConfig
import board
try:
    i2c = board.I2C()
    sensor = PS100SensorConfig(i2c, 0x40)
    print('   ✅ Sensor initialization successful')
except Exception as e:
    print(f'   ❌ Sensor test failed (normal if no hardware): {e}')
"

echo "4. Ready for TimescaleDB monitoring:"
echo "   Manual: ./start_ps100_timescale.sh"
echo "   Service: sudo systemctl start ps100-timescale-monitor"
echo "   Data query: Connect to TimescaleDB and query ps100_readings_1s table"
EOF

chmod +x test_ps100_timescale.sh

# Create SQL query examples
echo "📊 Creating SQL query examples..."
cat > timescale_queries.sql << 'EOF'
-- PS100 TimescaleDB Query Examples
-- Connect to your TimescaleDB and run these queries

-- 1. Latest readings for all panels (last 1 hour)
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
ORDER BY time DESC, panel_id;

-- 2. System performance summary (last 24 hours)
SELECT 
    DATE_TRUNC('hour', time) as hour,
    COUNT(DISTINCT panel_id) as active_panels,
    AVG(voltage_avg) as avg_system_voltage,
    SUM(power_avg) as total_system_power,
    SUM(energy_wh) / 1000.0 as total_energy_kwh,
    AVG(efficiency_percent) as avg_efficiency
FROM ps100_readings_1s
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', time)
ORDER BY hour DESC;

-- 3. Panel comparison (daily totals)
SELECT 
    panel_id,
    DATE(time) as date,
    AVG(voltage_avg) as avg_voltage,
    AVG(current_avg) as avg_current,
    AVG(power_avg) as avg_power,
    SUM(energy_wh) / 1000.0 as daily_energy_kwh,
    AVG(efficiency_percent) as avg_efficiency,
    COUNT(*) as data_points
FROM ps100_readings_1s
WHERE time > NOW() - INTERVAL '7 days'
GROUP BY panel_id, DATE(time)
ORDER BY date DESC, panel_id;

-- 4. Best performing hours (peak power times)
SELECT 
    DATE_TRUNC('hour', time) as hour,
    panel_id,
    AVG(power_avg) as avg_power,
    MAX(power_peak) as peak_power,
    AVG(efficiency_percent) as efficiency
FROM ps100_readings_1s
WHERE time > NOW() - INTERVAL '30 days'
  AND power_avg > 50  -- Only consider meaningful power generation
GROUP BY DATE_TRUNC('hour', time), panel_id
ORDER BY avg_power DESC
LIMIT 20;

-- 5. Alert and error summary
SELECT 
    panel_id,
    DATE(time) as date,
    SUM(alert_count) as total_alerts,
    SUM(error_count) as total_errors,
    COUNT(*) as total_readings,
    AVG(CASE WHEN alert_count > 0 THEN 1 ELSE 0 END) * 100 as alert_percentage
FROM ps100_readings_1s
WHERE time > NOW() - INTERVAL '7 days'
GROUP BY panel_id, DATE(time)
ORDER BY date DESC, panel_id;

-- 6. Continuous aggregate views (use these for fast queries over long periods)

-- 5-minute aggregates
SELECT * FROM ps100_readings_5min 
WHERE time > NOW() - INTERVAL '24 hours'
ORDER BY time DESC;

-- Hourly aggregates  
SELECT * FROM ps100_readings_1hour
WHERE time > NOW() - INTERVAL '7 days'
ORDER BY time DESC;

-- Daily aggregates
SELECT * FROM ps100_readings_daily
WHERE time > NOW() - INTERVAL '30 days'
ORDER BY time DESC;
EOF

echo ""
echo "✅ PS100 TimescaleDB Monitor Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "   1. Edit .env file with your TimescaleDB credentials"
echo "   2. Test setup: ./test_ps100_timescale.sh"
echo "   3. Manual start: ./start_ps100_timescale.sh"
echo "   4. Install service: sudo systemctl enable ps100-timescale-monitor"
echo "   5. Start service: sudo systemctl start ps100-timescale-monitor"
echo ""
echo "📊 Monitor service:"
echo "   Status: sudo systemctl status ps100-timescale-monitor"
echo "   Logs: sudo journalctl -u ps100-timescale-monitor -f"
echo "   Stop: sudo systemctl stop ps100-timescale-monitor"
echo ""
echo "🗄️  TimescaleDB Features:"
echo "   • High-frequency sampling (10 Hz) with 1-second averaging"
echo "   • Permanent data retention with compression"
echo "   • Continuous aggregates (5min, 1hour, daily)"
echo "   • Time-series optimized queries"
echo ""
echo "📊 Data Access:"
echo "   • Main table: ps100_readings_1s (1-second averages)"
echo "   • Aggregates: ps100_readings_5min, ps100_readings_1hour, ps100_readings_daily"
echo "   • Query examples: timescale_queries.sql"
echo ""
echo "⚠️  IMPORTANT: Make sure your TimescaleDB server is running and accessible!"
