"""
Stop Loss Manager
Manages stop-loss orders for day trading positions.
Handles:
- Initial hard stops
- Trailing stops
- Stop updates based on price movement
"""

from typing import Dict, List, Optional
from ..utils import logger
from config import DAY_TRADING_CONFIG

class StopLossManager:
    """Manages stop losses for active positions"""
    
    def __init__(self):
        self.active_stops: Dict[str, float] = {}  # {symbol: stop_price}
        self.trailing_enabled = DAY_TRADING_CONFIG.get('enable_trailing_stops', True)
        self.trail_pct = DAY_TRADING_CONFIG.get('trailing_stop_pct', 2.0) / 100.0
        
    def set_stop_loss(self, symbol: str, stop_price: float):
        """Set initial stop loss for a position"""
        self.active_stops[symbol] = stop_price
        logger.info(f"🛑 Stop-loss set for {symbol} at ${stop_price:.2f}")
        
    def get_stop_price(self, symbol: str) -> Optional[float]:
        """Get current stop price for a symbol"""
        return self.active_stops.get(symbol)
        
    def check_stops(self, current_prices: Dict[str, float]) -> List[str]:
        """
        Check if any stops are hit.
        Returns list of symbols to exit.
        """
        to_exit = []
        for symbol, stop_price in self.active_stops.items():
            current_price = current_prices.get(symbol)
            
            if current_price and current_price <= stop_price:
                logger.warning(f"🚨 STOP HIT: {symbol} at ${current_price:.2f} (Stop: ${stop_price:.2f})")
                to_exit.append(symbol)
                
        return to_exit
        
    def update_trailing_stops(self, current_prices: Dict[str, float]):
        """
        Update trailing stops if price moves in favor.
        """
        if not self.trailing_enabled:
            return
            
        for symbol, current_price in current_prices.items():
            if symbol not in self.active_stops:
                continue
                
            current_stop = self.active_stops[symbol]
            
            # Calculate new potential stop
            # If price moves up, stop moves up to maintain trail_pct distance
            # But we only move stop UP, never down (for long positions)
            
            # Simple trailing logic: Stop is always max(current_stop, price * (1 - trail_pct))
            new_stop = current_price * (1 - self.trail_pct)
            
            if new_stop > current_stop:
                self.active_stops[symbol] = new_stop
                logger.info(f"📈 Trailing stop updated for {symbol}: ${current_stop:.2f} -> ${new_stop:.2f}")

    def clear_stop(self, symbol: str):
        """Remove stop loss for a symbol (e.g. after exit)"""
        if symbol in self.active_stops:
            del self.active_stops[symbol]

# Global instance
stop_loss_manager = StopLossManager()
