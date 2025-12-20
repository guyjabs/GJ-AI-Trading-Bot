
import sys
import os
import logging
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from src.data.stock_data import stock_data_provider
from src.scalper import Scalper

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestCrypto")

def test_data_fetch():
    logger.info("--- Testing Data Fetch (BTC/USD) ---")
    symbol = "BTC/USD"
    data = stock_data_provider.fetch_stock_data(symbol)
    
    if data and data.get('current_price', 0) > 0:
        logger.info(f"✅ Successfully fetched data for {symbol}")
        logger.info(f"Price: {data['current_price']}")
        logger.info(f"Name/Symbol in data: {data.get('symbol')}")
    else:
        logger.error(f"❌ Failed to fetch data for {symbol}")
        print(data)

def test_scalper_simulation():
    logger.info("\n--- Testing Scalper Simulation ---")
    
    # Initialize Scalper
    scalper = Scalper()
    
    # Mock Alpaca for safety
    class MockAlpaca:
        def get_crypto_quote(self, symbol):
            # Return fake quote
            import random
            base = 50000 if 'BTC' in symbol else 3000
            price = base + random.uniform(-100, 100)
            return {'mark_price': price}
            
        def get_crypto_positions(self):
            return [{'symbol': 'ETH/USD', 'quantity': 1.5, 'cost_basis': {'amount': 0}}]
            
        def buy_crypto(self, s, a):
            logger.info(f"mock_buy: {s}, {a}")
            
        def sell_crypto(self, s, a):
            logger.info(f"mock_sell: {s}, {a}")

    scalper.alpaca = MockAlpaca()
    scalper.min_volatility = 0.0001 # Super sensitive for test
    scalper.scan_interval = 0.1
    
    # Inject fake price history to trigger signal
    scalper.last_prices['BTC/USD'] = 50000.0
    scalper.last_prices['ETH/USD'] = 3000.0
    
    # Run one scan manually
    logger.info("Running scan iteration...")
    scalper._scan_market()
    
    # force a drop to test sell logic
    logger.info("Forcing price drop for sell signal...")
    scalper.last_prices['BTC/USD'] = 60000.0 # Price was high
    # Next fetch will be ~50k -> Huge drop -> Signal DOWN
    
    scalper._scan_market()
    
    # BTC should NOT sell (not owned in mock)
    # ETH should sell (owned in mock)
    
    logger.info("Forcing ETH drop...")
    scalper.last_prices['ETH/USD'] = 4000.0
    scalper._scan_market()

if __name__ == "__main__":
    test_data_fetch()
    test_scalper_simulation()
