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
