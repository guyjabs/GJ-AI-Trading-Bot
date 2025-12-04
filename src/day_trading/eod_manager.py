"""
End-of-Day Manager
Responsible for ensuring all day trading positions are closed before market close.
"""

from datetime import datetime, time
import pytz
from ..utils import logger
from ..api.alpaca import get_alpaca_client

class EODManager:
    """Manages end-of-day position closing for day trading"""
    
    def __init__(self, market_close_time="16:00", force_close_buffer_minutes=15):
        """
        Args:
            market_close_time: Market close time in HH:MM format (default 16:00)
            force_close_buffer_minutes: Minutes before close to force exit (default 15)
        """
        self.market_close_time = datetime.strptime(market_close_time, "%H:%M").time()
        self.buffer_minutes = force_close_buffer_minutes
        self.timezone = pytz.timezone('US/Eastern')
        
    def get_market_time(self):
        """Get current time in market timezone"""
        return datetime.now(self.timezone)
        
    def should_force_close(self) -> bool:
        """Check if we are in the force close window"""
        now = self.get_market_time().time()
        
        # Calculate force close time
        close_hour = self.market_close_time.hour
        close_minute = self.market_close_time.minute
        
        total_minutes = close_hour * 60 + close_minute
        force_minutes = total_minutes - self.buffer_minutes
        
        force_hour = force_minutes // 60
        force_minute = force_minutes % 60
        
        force_time = time(force_hour, force_minute)
        
        # Check if we're past force time but before close
        return force_time <= now < self.market_close_time
    
    def close_all_positions(self, portfolio):
        """
        Force close all open positions.
        
        Args:
            portfolio: Dictionary of current positions
        """
        if not portfolio:
            return
            
        logger.warning(f"🚨 EOD FORCE CLOSE INITIATED: Closing {len(portfolio)} positions")
        
        for symbol, position in portfolio.items():
            try:
                # Skip if already selling or crypto (optional, depending on strategy)
                if symbol.endswith('-USD'): # Skip crypto for EOD close? usually yes for stock day trading
                    continue
                    
                quantity = float(position.get('quantity', 0))
                if quantity > 0:
                    logger.info(f"📉 Force closing {symbol} ({quantity} shares)")
                    # Execute market sell
                    alpaca = get_alpaca_client()
                    if alpaca:
                        alpaca.sell_stock(symbol, quantity)
                    
            except Exception as e:
                logger.error(f"❌ Failed to force close {symbol}: {e}")
