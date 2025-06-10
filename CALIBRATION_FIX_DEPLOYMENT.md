# Solar Monitor - Calibration Fix Deployment Guide

## 🔧 Voltage Reading Issue - RESOLVED

**Problem**: INA228 sensor was showing voltage readings of 0.004-0.005V instead of expected 12-24V for solar panels.

**Root Cause**: Default calibration uses `(0.015Ω, 10A)` which is designed for high-current applications, not solar monitoring.

**Solution**: Use `(0.1Ω, 1A)` calibration optimized for 32V solar panel monitoring.

## 📦 What's Been Fixed

✅ **Created `sensor_calibration_patch.py`** - Modular calibration fix
✅ **Created `fix_sensor_calibration.py`** - Comprehensive calibration testing tool  
✅ **Updated `data_logger.py`** - Applied calibration fix to high-frequency logger
✅ **Updated `data_logger_avg.py`** - Applied calibration fix to averaged logger
✅ **Added voltage property alias** - Compatibility with official examples
✅ **Optimized sensor settings** - 64-sample averaging, longer conversion times

## 🚀 Deployment Instructions

### 1. Pull Latest Changes on Raspberry Pi
```bash
cd /path/to/solar-monitor
git pull origin main
```

### 2. Stop Current Service (if running)
```bash
sudo systemctl stop solar-monitor-avg
sudo systemctl status solar-monitor-avg
```

### 3. Test the Calibration Fix
```bash
# Test calibration scenarios
python3 fix_sensor_calibration.py

# Quick sensor test with new calibration
python3 test_sensor.py
```

### 4. Restart the Service
```bash
sudo systemctl start solar-monitor-avg
sudo systemctl status solar-monitor-avg

# Monitor logs
sudo journalctl -u solar-monitor-avg -f
```

### 5. Verify Correct Readings
The logs should now show:
- **Voltage**: 12-24V (instead of 0.004V)
- **Current**: Realistic mA values for your solar setup
- **Power**: Calculated correctly from V×I

## 🎯 Expected Results

**Before Fix:**
```
📋 Voltage: 0.004V
⚡ Current: 250.0mA  
🔌 Power: 1.0mW
```

**After Fix:**
```
📋 Voltage: 18.450V  ← Should be realistic solar voltage
⚡ Current: 145.2mA   ← Actual solar current
🔌 Power: 2680.1mW   ← Realistic solar power
```

## 🔍 Files Changed

- `sensor_calibration_patch.py` - **NEW**: Modular calibration fix
- `fix_sensor_calibration.py` - **NEW**: Calibration testing tool
- `data_logger.py` - **UPDATED**: Includes calibration fix
- `data_logger_avg.py` - **UPDATED**: Includes calibration fix

## 🐛 Troubleshooting

If voltage readings are still incorrect:

1. **Check sensor connection**: Ensure I2C is working
2. **Test calibration manually**: Run `fix_sensor_calibration.py`
3. **Verify environment**: Check if running in virtual environment
4. **Check logs**: Look for calibration application messages

## 📊 Database Impact

No database schema changes required. The existing tables will now receive correct voltage readings:

- **solar_readings** - High frequency data (10 Hz)
- **solar_readings_avg** - 1-second averages

Previous incorrect readings will remain in the database but new data will be accurate.

## ✅ Verification Checklist

- [ ] Git pull completed successfully
- [ ] Service stopped cleanly
- [ ] Calibration test shows correct voltages (>5V)
- [ ] Service restarted successfully  
- [ ] Logs show "Applied solar calibration (0.1Ω, 1A)"
- [ ] Real-time readings show realistic solar voltages
- [ ] Database receives correct values

## 🎉 Success!

Your solar monitoring system should now provide accurate voltage, current, and power readings suitable for solar panel analysis and energy monitoring.
