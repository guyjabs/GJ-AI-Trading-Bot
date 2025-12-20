
import sys
import os
import time
import logging

# Add project root to path
sys.path.append(os.getcwd())

from src.scalper import Scalper

# Setup logging to console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crypto_session.log")
    ]
)

logger = logging.getLogger("SessionRunner")

def run_session():
    logger.info("Initializing Scalper for Real Paper Trading Session...")
    scalper = Scalper()
    
    # Ensure volatility is low enough to maybe trigger *something* or just observe scanning
    # Default is 0.002 (0.2%). Let's keep it real.
    
    logger.info(f"Targeting {len(scalper.symbols)} Crypto Symbols.")
    logger.info("Starting Scalper...")
    scalper.start_scalping()
    
    duration = 60
    logger.info(f"Running for {duration} seconds...")
    
    try:
        for i in range(duration):
            time.sleep(1)
            if i % 10 == 0:
                print(f"[{i}/{duration}s] Scalper running... Active Trades: {len(scalper.active_trades)}")
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        
    logger.info("Stopping Scalper...")
    scalper.stop_scalping()
    
    # Print Summary
    logger.info("--- Session Summary ---")
    logger.info(f"Active Potential Trades Triggered: {len(scalper.active_trades)}")
    for symbol, trade in scalper.active_trades.items():
        logger.info(f"  {symbol}: {trade['signal']} @ {trade['price']} ({trade['change']*100:.3f}%)")

if __name__ == "__main__":
    run_session()
