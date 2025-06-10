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
