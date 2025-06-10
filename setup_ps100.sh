#!/bin/bash
# PS100 Solar Monitor Setup Script
# Updated: June 10, 2025
# Anker SOLIX PS100 Solar Panel Monitoring System

set -e  # Exit on any error

echo "🌞 PS100 Solar Monitor Setup"
echo "============================"
echo "Setting up monitoring for Anker SOLIX PS100 solar panels"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This setup is optimized for Raspberry Pi"
    echo "   Some features may not work on other systems"
    echo ""
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $PYTHON_VERSION"

if [ "$(printf '%s\n' "$PYTHON_VERSION" "3.8" | sort -V | head -n1)" != "3.8" ]; then
    echo "❌ Python 3.8+ required, found $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
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

# Install system dependencies for hardware
echo "🔧 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-smbus \
    i2c-tools \
    git \
    sqlite3 \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7 \
    libtiff5

# Enable I2C
echo "🔗 Enabling I2C interface..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    echo "   I2C enabled in /boot/config.txt"
else
    echo "   I2C already enabled"
fi

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Create directories
echo "📁 Creating directories..."
mkdir -p config
mkdir -p logs
mkdir -p data
mkdir -p web/static
mkdir -p web/templates

# Test I2C connectivity
echo "🔍 Testing I2C connectivity..."
if command -v i2cdetect >/dev/null 2>&1; then
    echo "   Scanning I2C bus 1 for devices..."
    i2cdetect -y 1 || echo "   No I2C devices detected or permission issue"
else
    echo "   i2cdetect not available, skipping I2C scan"
fi

# Test sensor initialization
echo "🧪 Testing PS100 sensor configuration..."
python3 -c "
try:
    from ps100_sensor_config import test_ps100_sensor
    print('✅ PS100 sensor configuration module loaded successfully')
    print('   Run python3 ps100_sensor_config.py to test with hardware')
except ImportError as e:
    print(f'❌ Failed to load PS100 sensor module: {e}')
except Exception as e:
    print(f'⚠️  Sensor module loaded but test failed: {e}')
    print('   This is normal if no hardware is connected')
"

# Test database setup
echo "🗄️  Testing database setup..."
python3 -c "
try:
    from ps100_database import PS100Database
    db = PS100Database()
    db.close()
    print('✅ Database setup successful')
except Exception as e:
    print(f'❌ Database setup failed: {e}')
"

# Create systemd service file
echo "⚙️  Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/ps100-monitor.service"

sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=PS100 Solar Panel Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$(pwd)/venv/bin/python3 $(pwd)/ps100_monitor.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

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

# Create configuration file if it doesn't exist
CONFIG_FILE="config/panel_specifications.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "📝 Configuration file already created at $CONFIG_FILE"
else
    echo "   Using existing configuration: $CONFIG_FILE"
fi

# Create startup script
echo "🚀 Creating startup script..."
cat > start_ps100_monitor.sh << 'EOF'
#!/bin/bash
# PS100 Solar Monitor Startup Script

cd "$(dirname "$0")"

echo "🌞 Starting PS100 Solar Monitor..."

# Activate virtual environment
source venv/bin/activate

# Check if service is running
if systemctl is-active --quiet ps100-monitor; then
    echo "📋 Service is already running"
    echo "   Use: sudo systemctl status ps100-monitor"
    echo "   Logs: sudo journalctl -u ps100-monitor -f"
else
    echo "🔄 Starting PS100 monitor..."
    python3 ps100_monitor.py
fi
EOF

chmod +x start_ps100_monitor.sh

# Create quick test script
echo "🧪 Creating quick test script..."
cat > test_ps100_setup.sh << 'EOF'
#!/bin/bash
# Quick test for PS100 setup

cd "$(dirname "$0")"
source venv/bin/activate

echo "🔍 PS100 Setup Test"
echo "=================="

# Test 1: Check I2C
echo "1. I2C Bus Scan:"
i2cdetect -y 1 2>/dev/null || echo "   No devices or permission issue"

# Test 2: Test sensor config
echo "2. Sensor Configuration Test:"
python3 -c "
from ps100_sensor_config import PS100SensorConfig
import board
try:
    i2c = board.I2C()
    sensor = PS100SensorConfig(i2c, 0x40)
    print('   ✅ Sensor initialization successful')
except Exception as e:
    print(f'   ❌ Sensor test failed: {e}')
"

# Test 3: Database test
echo "3. Database Test:"
python3 -c "
from ps100_database import PS100Database
try:
    db = PS100Database()
    db.add_panel('TEST_PANEL', 'Test Location', '0x40')
    summary = db.get_panel_summary('TEST_PANEL')
    db.close()
    print('   ✅ Database test successful')
except Exception as e:
    print(f'   ❌ Database test failed: {e}')
"

echo "4. Ready to run:"
echo "   Manual: ./start_ps100_monitor.sh"
echo "   Service: sudo systemctl start ps100-monitor"
EOF

chmod +x test_ps100_setup.sh

echo ""
echo "✅ PS100 Solar Monitor Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "   1. Connect your Anker SOLIX PS100 panel(s) via INA228 sensor(s)"
echo "   2. Test setup: ./test_ps100_setup.sh"
echo "   3. Manual start: ./start_ps100_monitor.sh" 
echo "   4. Install service: sudo systemctl enable ps100-monitor"
echo "   5. Start service: sudo systemctl start ps100-monitor"
echo ""
echo "📊 Monitor service:"
echo "   Status: sudo systemctl status ps100-monitor"
echo "   Logs: sudo journalctl -u ps100-monitor -f"
echo "   Stop: sudo systemctl stop ps100-monitor"
echo ""
echo "🔧 Configuration file: config/panel_specifications.yaml"
echo "🗄️  Database file: ps100_solar.db"
echo "📝 Log file: ps100_monitor.log"
echo ""

# Check if reboot needed for I2C
if [ ! -f /sys/class/i2c-adapter/i2c-1/name ]; then
    echo "⚠️  REBOOT REQUIRED for I2C changes to take effect"
    echo "   Run: sudo reboot"
fi
