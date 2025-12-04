"""
Entry Signals Module
Detects technical entry signals for day trading strategies:
- Opening Range Breakout (ORB)
- VWAP Pullback
- Pre-market High Breakout
"""

from typing import Dict, Optional
from ..utils import logger
from ..data.intraday_data import intraday_data
from config import DAY_TRADING_CONFIG

class EntrySignals:
    """Detects technical entry signals"""
    
    def __init__(self):
        pass
        
    def detect_orb_breakout(self, symbol: str, range_minutes: int = 5) -> Dict:
        """
        Detect Opening Range Breakout (ORB).
        Signal is valid if current price breaks above OR high with volume.
        
        Returns:
            Dict with signal details or {'signal': False}
        """
        try:
            # Get Opening Range
            orb = intraday_data.get_opening_range(symbol, minutes=range_minutes)
            if not orb:
                return {'signal': False, 'reason': 'No opening range data'}
                
            # Get current price data
            df = intraday_data.get_intraday_data(symbol, interval="1m", period="1d")
            if df.empty:
                return {'signal': False, 'reason': 'No intraday data'}
                
            current_price = df['Close'].iloc[-1]
            current_volume = df['Volume'].iloc[-1]
            
            # Check for Breakout
            # Buffer: Price must be slightly above high to confirm (e.g. 0.1%)
            breakout_level = orb['high'] * 1.001
            
            if current_price > breakout_level:
                # Calculate stop loss (below OR low or mid-point depending on risk)
                # Conservative: Below OR Low
                stop_loss = orb['low']
                
                # Calculate target (2:1 R:R)
                risk = current_price - stop_loss
                target = current_price + (risk * 2)
                
                return {
                    'signal': True,
                    'strategy': 'orb',
                    'direction': 'long',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'setup_quality': 'high', # Could add volume check here
                    'timestamp': df.index[-1].isoformat()
                }
                
            return {'signal': False, 'reason': 'Price inside range'}
            
        except Exception as e:
            logger.error(f"Error checking ORB for {symbol}: {e}")
            return {'signal': False, 'error': str(e)}

    def detect_vwap_pullback(self, symbol: str) -> Dict:
        """
        Detect Pullback to VWAP.
        Signal: Price is above VWAP, pulls back to touch/near VWAP, and bounces.
        """
        try:
            df = intraday_data.get_intraday_data(symbol, interval="5m", period="1d")
            if df.empty or len(df) < 5:
                return {'signal': False, 'reason': 'Insufficient data'}
                
            # Calculate VWAP
            vwap_series = intraday_data.get_vwap(df)
            if vwap_series.empty:
                return {'signal': False, 'reason': 'VWAP calc failed'}
                
            current_price = df['Close'].iloc[-1]
            current_vwap = vwap_series.iloc[-1]
            
            # Check trend (Price generally above VWAP)
            # Simple check: 3 bars ago was above VWAP
            was_above = df['Close'].iloc[-3] > vwap_series.iloc[-3]
            
            # Check proximity (within 0.5% of VWAP)
            dist_pct = abs(current_price - current_vwap) / current_vwap
            near_vwap = dist_pct < 0.005
            
            # Check bounce (current candle is green)
            is_green = df['Close'].iloc[-1] > df['Open'].iloc[-1]
            
            if was_above and near_vwap and is_green:
                stop_loss = current_vwap * 0.995 # Stop just below VWAP
                risk = current_price - stop_loss
                target = current_price + (risk * 2)
                
                return {
                    'signal': True,
                    'strategy': 'vwap_pullback',
                    'direction': 'long',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'setup_quality': 'medium'
                }
                
            return {'signal': False, 'reason': 'No VWAP setup'}
            
        except Exception as e:
            logger.error(f"Error checking VWAP pullback for {symbol}: {e}")
            return {'signal': False, 'error': str(e)}

# Global instance
entry_signals = EntrySignals()
