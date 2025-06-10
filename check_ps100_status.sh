#!/bin/bash
# PS100 System Status Check
# Quick status check for PS100 solar monitoring system

echo "🌞 PS100 Solar Monitor - System Status"
echo "======================================"

# Check if in correct directory
if [ ! -f "ps100_monitor.py" ]; then
    echo "❌ Not in PS100 solar monitor directory"
    exit 1
fi

# Check Python environment
echo "🐍 Python Environment:"
if [ -d "venv" ]; then
    echo "   ✅ Virtual environment exists"
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "   ✅ Virtual environment activated: $VIRTUAL_ENV"
    else
        echo "   ⚠️  Virtual environment not activated (run: source venv/bin/activate)"
    fi
else
    echo "   ❌ Virtual environment missing (run setup script)"
fi

# Check dependencies
echo "📦 Dependencies:"
if [ -f "requirements.txt" ]; then
    echo "   ✅ requirements.txt exists"
    if command -v pip >/dev/null 2>&1; then
        MISSING=$(pip freeze -r requirements.txt 2>&1 | grep "not installed" | wc -l)
        if [ "$MISSING" -eq 0 ]; then
            echo "   ✅ All dependencies installed"
        else
            echo "   ⚠️  $MISSING missing dependencies (run: pip install -r requirements.txt)"
        fi
    fi
else
    echo "   ❌ requirements.txt missing"
fi

# Check configuration
echo "⚙️  Configuration:"
if [ -f "config/panel_specifications.yaml" ]; then
    echo "   ✅ Panel configuration exists"
else
    echo "   ⚠️  Panel configuration missing"
fi

if [ -f ".env" ]; then
    echo "   ✅ Environment file exists"
    if grep -q "TIMESCALE_HOST" .env 2>/dev/null; then
        echo "   ✅ TimescaleDB configuration detected"
    else
        echo "   ℹ️  SQLite configuration (no TimescaleDB)"
    fi
else
    echo "   ⚠️  Environment file missing (copy from .env.example)"
fi

# Check I2C
echo "🔗 I2C Status:"
if [ -e "/dev/i2c-1" ]; then
    echo "   ✅ I2C device exists"
    if command -v i2cdetect >/dev/null 2>&1; then
        DEVICES=$(i2cdetect -y 1 2>/dev/null | grep -o '[0-9a-f][0-9a-f]' | wc -l)
        if [ "$DEVICES" -gt 0 ]; then
            echo "   ✅ $DEVICES I2C devices detected"
        else
            echo "   ⚠️  No I2C devices detected"
        fi
    else
        echo "   ⚠️  i2c-tools not installed (sudo apt install i2c-tools)"
    fi
else
    echo "   ❌ I2C not enabled (check /boot/config.txt)"
fi

# Check services
echo "🔧 Services:"
for service in "ps100-monitor" "ps100-timescale-monitor"; do
    if systemctl list-unit-files | grep -q "$service"; then
        STATUS=$(systemctl is-active "$service" 2>/dev/null || echo "inactive")
        if [ "$STATUS" = "active" ]; then
            echo "   ✅ $service: running"
        else
            echo "   ⚠️  $service: $STATUS"
        fi
    else
        echo "   ℹ️  $service: not installed"
    fi
done

# Check log files
echo "📝 Log Files:"
for log in "ps100_monitor.log" "ps100_timescale_monitor.log"; do
    if [ -f "$log" ]; then
        SIZE=$(du -h "$log" | cut -f1)
        LINES=$(wc -l < "$log")
        echo "   ✅ $log: $SIZE ($LINES lines)"
    else
        echo "   ℹ️  $log: not found"
    fi
done

# Check database
echo "🗄️  Database:"
if [ -f "ps100_solar.db" ]; then
    SIZE=$(du -h "ps100_solar.db" | cut -f1)
    echo "   ✅ SQLite database: $SIZE"
fi

if [ -f ".env" ] && grep -q "TIMESCALE_HOST" .env 2>/dev/null; then
    echo "   ℹ️  TimescaleDB: configured (test connection manually)"
fi

echo ""
echo "🎯 Quick Actions:"
echo "   Test hardware: python3 ps100_sensor_config.py"
echo "   Start SQLite: sudo systemctl start ps100-monitor"
echo "   Start TimescaleDB: sudo systemctl start ps100-timescale-monitor"
echo "   View logs: sudo journalctl -u ps100-monitor -f"
echo "   Status: sudo systemctl status ps100-monitor"
