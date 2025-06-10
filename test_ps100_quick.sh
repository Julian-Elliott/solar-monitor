#!/bin/bash
# PS100 Quick Test Script
# Tests all components of the PS100 solar monitoring system

cd "$(dirname "$0")"

echo "🧪 PS100 Solar Monitor - Quick Test"
echo "==================================="

# Activate virtual environment if it exists
if [ -d "venv" ] && [ -z "$VIRTUAL_ENV" ]; then
    echo "🔌 Activating virtual environment..."
    source venv/bin/activate
fi

echo ""
echo "1️⃣  Testing PS100 Sensor Configuration..."
python3 -c "
try:
    from ps100_sensor_config import PS100SensorConfig
    print('   ✅ PS100 sensor module loaded successfully')
    
    # Test with mock I2C if no hardware
    try:
        import board
        i2c = board.I2C()
        sensor = PS100SensorConfig(i2c, 0x40)
        print('   ✅ Hardware sensor initialization successful')
        
        # Test reading
        data = sensor.read_panel_data()
        print(f'   ✅ Test reading: {data[\"voltage\"]:.2f}V, {data[\"current\"]:.2f}A, {data[\"power\"]:.1f}W')
        
    except Exception as e:
        print(f'   ⚠️  Hardware test failed (normal if no hardware): {e}')
        
except Exception as e:
    print(f'   ❌ PS100 sensor module test failed: {e}')
"

echo ""
echo "2️⃣  Testing SQLite Database..."
python3 -c "
try:
    from ps100_database import PS100Database
    db = PS100Database()
    print('   ✅ SQLite database connection successful')
    
    # Test panel operations
    db.add_panel('TEST_PANEL', 'Test Location', '0x40', 'Quick test panel')
    print('   ✅ Panel creation test passed')
    
    # Test data logging
    db.log_reading('TEST_PANEL', 25.0, 3.5, 87.5, 30.0)
    print('   ✅ Data logging test passed')
    
    # Test data retrieval
    recent = db.get_recent_readings('TEST_PANEL', hours=1)
    print(f'   ✅ Data retrieval test passed ({len(recent)} records)')
    
    db.close()
    
except Exception as e:
    print(f'   ❌ SQLite database test failed: {e}')
"

echo ""
echo "3️⃣  Testing TimescaleDB (if configured)..."
if [ -f ".env" ] && grep -q "TIMESCALE_HOST" .env 2>/dev/null; then
    python3 -c "
try:
    from ps100_timescaledb import PS100TimescaleDB
    db = PS100TimescaleDB()
    print('   ✅ TimescaleDB connection successful')
    
    # Test panel operations
    db.add_panel('TEST_PANEL_TS', 'Test Location TS', '0x40', 'TimescaleDB test panel')
    print('   ✅ TimescaleDB panel creation test passed')
    
    # Test data buffering
    db.buffer_reading('TEST_PANEL_TS', 26.0, 3.7, 96.2, 28.5)
    print('   ✅ TimescaleDB data buffering test passed')
    
    db.force_flush()
    print('   ✅ TimescaleDB data flush test passed')
    
    db.close()
    
except Exception as e:
    print(f'   ❌ TimescaleDB test failed: {e}')
    print(f'   ℹ️  Check .env file and TimescaleDB server connection')
"
else
    echo "   ℹ️  TimescaleDB not configured (check .env file)"
fi

echo ""
echo "4️⃣  Testing I2C Connectivity..."
if command -v i2cdetect >/dev/null 2>&1; then
    echo "   🔍 Scanning I2C bus 1 for devices..."
    i2cdetect -y 1 2>/dev/null | grep -E '[0-9a-f][0-9a-f]' && echo "   ✅ I2C devices detected" || echo "   ⚠️  No I2C devices found"
else
    echo "   ⚠️  i2cdetect not available (install with: sudo apt install i2c-tools)"
fi

echo ""
echo "5️⃣  Testing Configuration Files..."
if [ -f "config/panel_specifications.yaml" ]; then
    echo "   ✅ Panel specifications config exists"
else
    echo "   ⚠️  Panel specifications config missing"
fi

if [ -f ".env" ]; then
    echo "   ✅ Environment configuration exists"
else
    echo "   ⚠️  Environment configuration missing (copy from .env.example)"
fi

echo ""
echo "6️⃣  Testing Service Installation..."
for service in "ps100-monitor" "ps100-timescale-monitor"; do
    if systemctl list-unit-files | grep -q "$service"; then
        echo "   ✅ $service service installed"
    else
        echo "   ℹ️  $service service not installed (run setup script)"
    fi
done

echo ""
echo "✅ PS100 Quick Test Complete!"
echo ""
echo "🚀 Next Steps:"
if [ ! -f ".env" ]; then
    echo "   1. Copy environment config: cp .env.example .env"
    echo "   2. Edit .env with your settings: nano .env"
fi
echo "   3. Run setup: ./setup_ps100.sh (SQLite) or ./setup_ps100_timescale.sh (TimescaleDB)"
echo "   4. Start monitoring: sudo systemctl start ps100-monitor"
echo "   5. Check status: ./check_ps100_status.sh"
