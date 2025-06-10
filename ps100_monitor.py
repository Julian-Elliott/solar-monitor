#!/usr/bin/env python3
"""
PS100 Solar Monitor - TimescaleDB Implementation
Main entry point for the PS100 monitoring system
"""

import sys
import asyncio
import argparse

from src.monitoring import PS100Monitor


def main():
    """Main entry point with command line interface"""
    parser = argparse.ArgumentParser(description='PS100 Solar Monitor - TimescaleDB')
    parser.add_argument('--addresses', nargs='+', type=lambda x: int(x, 0), 
                       default=[0x40], help='I2C addresses (e.g., 0x40 0x41)')
    parser.add_argument('--interval', type=float, default=1.0, help='Read interval in seconds')
    parser.add_argument('--test', action='store_true', help='Run test mode (single reading)')
    parser.add_argument('--status', action='store_true', help='Show current status')
    
    args = parser.parse_args()
    
    try:
        monitor = PS100Monitor(addresses=args.addresses)
        
        if args.test:
            # Test mode - single reading
            print("🧪 PS100 Test Mode")
            for panel_id, sensor in monitor.sensors.items():
                reading = sensor.read()
                if reading:
                    print(f"📊 {panel_id}:")
                    print(f"   Voltage: {reading['voltage']:.2f}V")
                    print(f"   Current: {reading['current']:.2f}A") 
                    print(f"   Power: {reading['power']:.1f}W")
                    print(f"   Efficiency: {reading['efficiency_percent']:.1f}%")
                    print(f"   Conditions: {reading['conditions']}")
                    
        elif args.status:
            # Status mode
            status = monitor.status()
            print(f"📊 PS100 Status:")
            print(f"   Sensors: {status['sensors']}")
            print(f"   Database: {status['database']}")
            if status['latest_reading']:
                latest = status['latest_reading']
                print(f"   Latest: {latest['power']:.1f}W - {latest['conditions']}")
                
        else:
            # Monitor mode
            asyncio.run(monitor.run_monitor(args.interval))
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
