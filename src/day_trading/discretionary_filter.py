"""
Discretionary Filter Module
Adds a layer of "market awareness" to filter trades based on 
broad market trends (SPY, QQQ) and time of day.
"""

from datetime import datetime
from ..utils import logger
from ..data.intraday_data import intraday_data
from config import DAY_TRADING_CONFIG

class DiscretionaryFilter:
    """Filters trades based on market context"""
    
    def __init__(self):
        pass
        
    def check_market_alignment(self, direction: str = 'long') -> bool:
        """
        Check if broad market (SPY, QQQ) supports the trade direction.
        For 'long' trades, we want SPY/QQQ to be uptrending or neutral.
        """
        if not DAY_TRADING_CONFIG.get('require_spy_alignment', True):
            return True
            
        try:
            # Check SPY Trend (using 5m data)
            spy_df = intraday_data.get_intraday_data("SPY", interval="5m", period="1d")
            if spy_df.empty:
                return True # Fail open if no data
                
            # Simple trend: Current price > 20-period SMA
            spy_price = spy_df['Close'].iloc[-1]
            spy_ma = spy_df['Close'].rolling(window=20).mean().iloc[-1]
            
            spy_bullish = spy_price > spy_ma
            
            if direction == 'long' and not spy_bullish:
                logger.info("🚫 Market Filter: SPY is bearish, skipping long trade")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking market alignment: {e}")
            return True # Fail open

    def check_time_of_day(self) -> bool:
        """
        Avoid trading during low-volume "lunch hour" (12:00 - 14:00 ET).
        """
        if not DAY_TRADING_CONFIG.get('avoid_lunch_hour', True):
            return True
            
        now = datetime.now().time()
        lunch_start = datetime.strptime("12:00", "%H:%M").time()
        lunch_end = datetime.strptime("14:00", "%H:%M").time()
        
        if lunch_start <= now < lunch_end:
            logger.info("🚫 Time Filter: Lunch hour (low volume), skipping trade")
            return False
            
        return True

# Global instance
discretionary_filter = DiscretionaryFilter()
