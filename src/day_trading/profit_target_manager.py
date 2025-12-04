"""
Profit Target Manager
Calculates profit targets and manages scale-out exits.
"""

from typing import Dict, Optional
from ..utils import logger
from config import DAY_TRADING_CONFIG

class ProfitTargetManager:
    """Manages profit targets and scaling out"""
    
    def __init__(self):
        self.active_targets: Dict[str, float] = {}  # {symbol: target_price}
        self.entry_prices: Dict[str, float] = {}    # {symbol: entry_price}
        self.initial_stops: Dict[str, float] = {}   # {symbol: initial_stop}
        
    def set_target(self, symbol: str, entry_price: float, stop_price: float, min_rr: float = 2.0):
        """
        Calculate and set profit target based on risk.
        Target = Entry + (Risk * R:R)
        """
        risk = entry_price - stop_price
        if risk <= 0:
            logger.warning(f"Invalid risk calculation for {symbol} (Entry: {entry_price}, Stop: {stop_price})")
            return
            
        target_price = entry_price + (risk * min_rr)
        
        self.active_targets[symbol] = target_price
        self.entry_prices[symbol] = entry_price
        self.initial_stops[symbol] = stop_price
        
        logger.info(f"🎯 Target set for {symbol} at ${target_price:.2f} ({min_rr}R)")
        
    def check_targets(self, current_prices: Dict[str, float]) -> Dict[str, Dict]:
        """
        Check if targets are reached.
        Returns dict of actions: {symbol: {'action': 'sell', 'qty_pct': 1.0}}
        """
        actions = {}
        
        for symbol, target_price in self.active_targets.items():
            current_price = current_prices.get(symbol)
            if not current_price:
                continue
                
            if current_price >= target_price:
                logger.info(f"🎯 TARGET REACHED: {symbol} at ${current_price:.2f} >= ${target_price:.2f}")
                actions[symbol] = {
                    'action': 'sell',
                    'qty_pct': 1.0, # Full exit for now, could implement scaling
                    'reason': 'target_reached'
                }
                
        return actions
        
    def clear_target(self, symbol: str):
        """Remove target for a symbol"""
        if symbol in self.active_targets:
            del self.active_targets[symbol]
        if symbol in self.entry_prices:
            del self.entry_prices[symbol]
        if symbol in self.initial_stops:
            del self.initial_stops[symbol]

# Global instance
profit_target_manager = ProfitTargetManager()
