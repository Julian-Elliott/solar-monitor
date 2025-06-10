#!/bin/bash
# PS100 TimescaleDB Test Script

cd "$(dirname "$0")"

echo "🧪 PS100 TimescaleDB Test"
echo "========================="

# Load environment
source ../../config/.env

echo "1️⃣ Testing TimescaleDB connection..."
python3 -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
try:
    conn = psycopg2.connect(
        host=os.getenv('TIMESCALE_HOST'),
        port=os.getenv('TIMESCALE_PORT'),
        user=os.getenv('TIMESCALE_USER'), 
        password=os.getenv('TIMESCALE_PASSWORD'),
        database=os.getenv('TIMESCALE_DATABASE')
    )
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM ps100_readings;')
    count = cursor.fetchone()[0]
    print(f'✅ TimescaleDB OK - {count} records')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
    exit(1)
"

echo "2️⃣ Testing sensor and data storage..."
timeout 10s python3 ../../ps100_monitor.py --interval 1 &
MONITOR_PID=$!
sleep 5
kill $MONITOR_PID 2>/dev/null || true
wait $MONITOR_PID 2>/dev/null || true

echo "3️⃣ Checking stored data..."
python3 -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
try:
    conn = psycopg2.connect(
        host=os.getenv('TIMESCALE_HOST'),
        port=os.getenv('TIMESCALE_PORT'),
        user=os.getenv('TIMESCALE_USER'),
        password=os.getenv('TIMESCALE_PASSWORD'), 
        database=os.getenv('TIMESCALE_DATABASE')
    )
    cursor = conn.cursor()
    cursor.execute('SELECT time, panel_id, power, conditions FROM ps100_readings ORDER BY time DESC LIMIT 3;')
    rows = cursor.fetchall()
    for row in rows:
        print(f'   {row[0]} | {row[1]} | {row[2]:.1f}W | {row[3]}')
    conn.close()
except Exception as e:
    print(f'❌ Query failed: {e}')
"

echo "✅ TimescaleDB test complete!"
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
