
import sys
import os
sys.path.append(os.getcwd())

from src.day_trading.day_screener import day_screener

print("Scanning Gappers...")
gappers = day_screener.scan_gappers()
print("Gappers:", gappers)

print("\nScanning Momentum...")
momentum = day_screener.scan_momentum()
print("Momentum:", momentum)
