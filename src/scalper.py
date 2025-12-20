import time
import threading
import logging
import random
from datetime import datetime
from typing import List, Dict, Optional

from src.api.alpaca import get_alpaca_client
from config import ALPACA_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scalper")

class Scalper:
    def __init__(self):
        self.running = False
        # Top 30 Crypto Pairs on Alpaca
        self.symbols = [
            'BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'SHIB/USD',
            'AVAX/USD', 'LINK/USD', 'LTC/USD', 'BCH/USD', 'UNI/USD',
            'AAVE/USD', 'ALGO/USD', 'ATOM/USD', 'BAT/USD', 'COMP/USD',
            'CRV/USD', 'DOT/USD', 'ETC/USD', 'FIL/USD', 'GRT/USD',
            'LDO/USD', 'MATIC/USD', 'MKR/USD', 'NEAR/USD', 'SNX/USD',
            'SUSHI/USD', 'XLM/USD', 'XTZ/USD', 'YFI/USD', 'ADA/USD'
        ]
        self.active_trades = {}
        self.scan_interval = 2.0  # Poll every 2 seconds to avoid rate limits
        self.thread = None
        self.lock = threading.Lock()
        
        # Initialize Alpaca Client
        self.alpaca = get_alpaca_client(
            api_key=ALPACA_CONFIG.get('api_key'),
            secret_key=ALPACA_CONFIG.get('secret_key'),
            paper=ALPACA_CONFIG.get('paper', True)
        )
        
        # Strategy Parameters
        self.min_volatility = 0.002  # 0.2% change 
        self.trade_amount = 1000.0   # $1000 per trade
        
        # State
        self.last_prices = {}

    def update_config(self, min_vol=None, tp=None, sl=None):
        """Update strategy parameters dynamically."""
        if min_vol is not None:
            self.min_volatility = float(min_vol)
        logger.info(f"⚡ Scalper config updated: Vol={self.min_volatility}")

    def start_scalping(self):
        """Start the scalping loop in a background thread."""
        if self.running:
            logger.warning("Scalper already running.")
            return
        
        logger.info(f"⚡ Scalper started. Monitoring {len(self.symbols)} tickers with real money/paper...")
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
        """Fetch prices and check for rapid movements."""
        for symbol in self.symbols:
            if not self.running: break
            
            try:
                current_price = self._get_price(symbol)
                if not current_price:
                    continue

                last_price = self.last_prices.get(symbol)
                self.last_prices[symbol] = current_price

                if last_price:
                    pct_change = (current_price - last_price) / last_price
                    
                    # Log significant moves
                    if abs(pct_change) >= self.min_volatility:
                        direction = "UP" if pct_change > 0 else "DOWN"
                        logger.info(f"⚡ [SCALP SIGNAL] {symbol} moved {pct_change*100:.4f}% {direction}")
                        
                        # Store signal for UI
                        with self.lock:
                            self.active_trades[symbol] = {
                                "signal": direction,
                                "price": current_price,
                                "change": pct_change,
                                "time": datetime.now().strftime("%H:%M:%S")
                            }
                        
                        # EXECUTE TRADE
                        side = 'buy' if direction == 'UP' else 'sell'
                        # For scalping, maybe we only BUY on breakouts (UP) or dip buy (DOWN)?
                        # Simple logic: Chase Momentum (Buy UP, Sell DOWN - assuming we hold it? No, we can short or sell holdings)
                        # Let's assume Long execution on UP signals.
                        
                        if direction == "UP":
                            self._execute_trade(symbol, 'buy', self.trade_amount, current_price)
                        elif direction == "DOWN":
                            # Use API to check current position before selling
                            try:
                                positions = self.alpaca.get_crypto_positions()
                                # Clean symbol for comparison if needed, but alpaca.py returns standard symbol from API
                                # Our self.symbols has 'BTC/USD', API usually returns same or 'BTCUSD' depending on normalization
                                # alpaca.py's get_crypto_positions normalizes to what? Let's check.
                                # It returns 'symbol' directly from API position.
                                
                                # Simple check: Do we have > 0 quantity?
                                owned = False
                                for pos in positions:
                                    if pos['symbol'] == symbol or pos['symbol'] == symbol.replace('/',''):
                                        if float(pos['quantity']) > 0:
                                            owned = True
                                            break
                                            
                                if owned:
                                    self._execute_trade(symbol, 'sell', self.trade_amount, current_price)
                                else:
                                    logger.info(f"⚠️ Signal SELL {symbol}, but not owned. Skipping.")
                            except Exception as e:
                                logger.error(f"Error checking positions for {symbol}: {e}")
                            
            except Exception as e:
                logger.debug(f"Error scanning {symbol}: {e}")

    def _get_price(self, symbol: str) -> Optional[float]:
        """Fetch real-time price from Alpaca."""
        try:
            # Requires Data API
            quote = self.alpaca.get_crypto_quote(symbol) 
            # Logic handled in alpaca.py adapter -> returns dict or object? 
            # Our adapter returns dict with 'mark_price' usually
            if quote and 'mark_price' in quote:
                return float(quote['mark_price'])
            return None
        except Exception as e:
            # logger.warn(f"Price fetch failed for {symbol}: {e}")
            return None

    def _execute_trade(self, symbol: str, side: str, notional_amount: float, price: float):
        """Execute a market order."""
        try:
            # Calculate quantity
            qty = notional_amount / price
            
            logger.info(f"🚀 EXECUTING {side.upper()} {symbol} (${notional_amount})...")
            
            response = None
            if side == 'buy':
                response = self.alpaca.buy_crypto(symbol, notional_amount)
            elif side == 'sell':
                response = self.alpaca.sell_crypto(symbol, notional_amount)
            
            # Check for success (Robinhood/Alpaca adapter style returns 'id' or 'state' on success, 'detail' on failure)
            if response and ('id' in response or response.get('state') == 'filled'):
                logger.info(f"✅ ORDER PLACED: {side.upper()} {symbol} (ID: {response.get('id')})")
            else:
                error_msg = response.get('detail') if response else "Unknown error"
                logger.error(f"❌ ORDER FAILED: {side.upper()} {symbol} - {error_msg}")
            
        except Exception as e:
            logger.error(f"❌ EXECUTION FAILED {side.upper()} {symbol}: {e}")
