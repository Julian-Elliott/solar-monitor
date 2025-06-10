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
