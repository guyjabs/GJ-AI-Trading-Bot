"""
Time Exit Manager
Manages time-based exits for stagnant trades.
"If it doesn't go, it goes."
"""

from datetime import datetime, timedelta
from typing import Dict, List
from ..utils import logger
from config import DAY_TRADING_CONFIG

class TimeExitManager:
    """Manages time-based exits"""
    
    def __init__(self):
        self.entry_times: Dict[str, datetime] = {}
        self.stagnation_minutes = DAY_TRADING_CONFIG.get('stagnation_exit_minutes', 20)
        
    def register_entry(self, symbol: str):
        """Register entry time for a new position"""
        self.entry_times[symbol] = datetime.now()
        
    def check_stagnation(self, symbol: str, current_pnl_pct: float) -> bool:
        """
        Check if trade is stagnant.
        Stagnant = Held > N minutes AND PnL is small (e.g. < 0.5%)
        """
        if symbol not in self.entry_times:
            return False
            
        entry_time = self.entry_times[symbol]
        time_held = datetime.now() - entry_time
        minutes_held = time_held.total_seconds() / 60
        
        if minutes_held >= self.stagnation_minutes:
            # Only exit if trade isn't working (PnL is small)
            # If we are up 5%, keep holding even if time passed
            if abs(current_pnl_pct) < 0.005: # Less than 0.5% move
                logger.warning(f"⏰ TIME EXIT: {symbol} stagnant for {minutes_held:.0f} min (PnL: {current_pnl_pct:.2%})")
                return True
                
        return False
        
    def clear_entry(self, symbol: str):
        """Remove entry time for a symbol"""
        if symbol in self.entry_times:
            del self.entry_times[symbol]

# Global instance
time_exit_manager = TimeExitManager()
