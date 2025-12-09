import time
import threading
import logging
import random
from datetime import datetime
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scalper")

class Scalper:
    def __init__(self):
        self.running = False
        self.symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'SHIB/USD']  # Volatile targets
        self.active_trades = {}
        self.scan_interval = 1.0  # High frequency: 1 second
        self.thread = None
        self.lock = threading.Lock()
        
        # Strategy Parameters (Penny Flipping)
        self.min_volatility = 0.001  # 0.1% change needed to interest us
        self.take_profit = 0.005     # 0.5% gain
        self.stop_loss = 0.003       # 0.3% loss
        
        # Mock Data State (for simulation if API limits hit)
        self.last_prices = {}

    def update_config(self, min_vol=None, tp=None, sl=None):
        """Update strategy parameters dynamically."""
        if min_vol is not None:
            self.min_volatility = float(min_vol)
        if tp is not None:
            self.take_profit = float(tp)
        if sl is not None:
            self.stop_loss = float(sl)
        logger.info(f"⚡ Scalper config updated: Vol={self.min_volatility}, TP={self.take_profit}, SL={self.stop_loss}")


    def start_scalping(self):
        """Start the scalping loop in a background thread."""
        if self.running:
            logger.warning("Scalper already running.")
            return
        
        logger.info("⚡ Scalper started. Monitoring tickers...")
        self.running = True
        self.thread = threading.Thread(target=self._scalp_loop, daemon=True)
        self.thread.start()

    def stop_scalping(self):
        """Stop the scalping loop."""
        if not self.running:
            return
            
        logger.info("⚡ Scalper stopping...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("⚡ Scalper stopped.")

    def get_status(self) -> Dict:
        """Return current status and active potential trades."""
        return {
            "running": self.running,
            "active_trades": self.active_trades,
            "monitored_symbols": self.symbols,
            "timestamp": datetime.now().isoformat()
        }

    def _scalp_loop(self):
        """Main loop for high-frequency scanning."""
        while self.running:
            try:
                self._scan_market()
                time.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Error in scalp loop: {e}")
                time.sleep(5)

    def _scan_market(self):
        """
        Fetch prices and check for rapid movements.
        In a real scenario, this would connect to a websocket for valid HFT.
        Here we simulate or poll.
        """
        for symbol in self.symbols:
            current_price = self._get_price(symbol)
            if not current_price:
                continue

            last_price = self.last_prices.get(symbol)
            self.last_prices[symbol] = current_price

            if last_price:
                pct_change = (current_price - last_price) / last_price
                
                # Logic: If price moves significantly in one interval
                if abs(pct_change) >= self.min_volatility:
                    direction = "UP" if pct_change > 0 else "DOWN"
                    logger.info(f"⚡ [SCALP SIGNAL] {symbol} moved {pct_change*100:.4f}% {direction}")
                    
                    # Store as a "potential trade" or "signal" for the UI
                    with self.lock:
                        self.active_trades[symbol] = {
                            "signal": direction,
                            "price": current_price,
                            "change": pct_change,
                            "time": datetime.now().strftime("%H:%M:%S")
                        }

    def _get_price(self, symbol: str) -> Optional[float]:
        """
        Mock price fetcher for stability. 
        Replace with self.alpaca.get_latest_trade(symbol).price in production.
        """
        # Simulated volatility for demonstration
        base_price = {
            'BTC/USD': 98000.0,
            'ETH/USD': 2700.0,
            'SOL/USD': 175.0,
            'DOGE/USD': 0.14,
            'SHIB/USD': 0.000025
        }.get(symbol, 100.0)
        
        last = self.last_prices.get(symbol, base_price)
        change = random.uniform(-0.002, 0.002) # +/- 0.2%
        return last * (1 + change)
