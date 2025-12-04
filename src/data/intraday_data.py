"""
Intraday Data Provider
Fetches real-time intraday data (1-min, 5-min bars) and calculates technical metrics
specifically for day trading: VWAP, RVOL, Opening Range, Pre-market Gap.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ..utils import logger

class IntradayDataProvider:
    """Provides intraday data and technical metrics for day trading"""
    
    def __init__(self):
        pass
        
    def get_intraday_data(self, symbol: str, interval: str = "5m", period: str = "1d") -> pd.DataFrame:
        """
        Fetch intraday data from yfinance.
        
        Args:
            symbol: Stock symbol
            interval: Bar interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
            period: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            
        Returns:
            DataFrame with Open, High, Low, Close, Volume
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No intraday data found for {symbol}")
                return pd.DataFrame()
                
            return df
        except Exception as e:
            logger.error(f"Error fetching intraday data for {symbol}: {e}")
            return pd.DataFrame()

    def get_premarket_gap(self, symbol: str) -> float:
        """
        Calculate pre-market gap percentage.
        Gap = (Open - Previous Close) / Previous Close
        
        Returns:
            Gap percentage (e.g., 3.5 for 3.5%)
        """
        try:
            ticker = yf.Ticker(symbol)
            # Get 5 days of history to ensure we have previous close
            hist = ticker.history(period="5d")
            
            if len(hist) < 2:
                return 0.0
                
            prev_close = hist['Close'].iloc[-2]
            
            # Try to get current pre-market price or open
            # yfinance history might not show pre-market well without specific args, 
            # but 'info' often has 'currentPrice' or 'open'
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('open') or hist['Close'].iloc[-1]
            
            if not current_price or not prev_close:
                return 0.0
                
            gap_pct = ((current_price - prev_close) / prev_close) * 100
            return gap_pct
            
        except Exception as e:
            logger.error(f"Error calculating gap for {symbol}: {e}")
            return 0.0

    def calculate_rvol(self, symbol: str) -> float:
        """
        Calculate Relative Volume (RVOL) vs 10-day average.
        RVOL = Current Volume / Average Volume for this time of day
        
        For simplicity in this version, we compare current accumulated volume 
        vs average daily volume scaled to the current time of day.
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            
            if hist.empty:
                return 0.0
                
            # Average daily volume over last 10 days (excluding today)
            avg_daily_vol = hist['Volume'].iloc[:-1].mean()
            
            if avg_daily_vol == 0:
                return 0.0
                
            # Current volume today
            current_vol = hist['Volume'].iloc[-1]
            
            # Simple RVOL approximation: 
            # Ideally we'd compare volume-at-time, but for now we'll use 
            # a simple ratio if it's end of day, or project it.
            # A better approach for real-time is:
            # RVOL = (Current Vol / Avg Daily Vol) / (Time Elapsed / Total Trading Time)
            
            # Let's use a simpler proxy: Current Volume / (Avg Vol / 6.5 hours * hours_elapsed)
            # Or just return volume ratio vs avg daily volume for now if scanning pre-market/early
            
            return current_vol / avg_daily_vol
            
        except Exception as e:
            logger.error(f"Error calculating RVOL for {symbol}: {e}")
            return 0.0

    def get_vwap(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate VWAP (Volume Weighted Average Price) for the given DataFrame.
        DF must have 'Close' (or 'High','Low','Close' avg) and 'Volume'.
        """
        try:
            if df.empty:
                return pd.Series()
            
            v = df['Volume'].values
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            return df.assign(vwap=(tp * v).cumsum() / v.cumsum())['vwap']
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return pd.Series()

    def get_opening_range(self, symbol: str, minutes: int = 5) -> dict:
        """
        Get Opening Range (High/Low) for the first N minutes of the trading day.
        """
        try:
            # Fetch 1-minute data for today
            df = self.get_intraday_data(symbol, interval="1m", period="1d")
            
            if df.empty or len(df) < minutes:
                return None
                
            # Assuming data starts at market open (9:30 AM ET)
            # Take first N rows
            first_n_bars = df.iloc[:minutes]
            
            orb_high = first_n_bars['High'].max()
            orb_low = first_n_bars['Low'].min()
            
            return {
                'high': orb_high,
                'low': orb_low,
                'range': orb_high - orb_low
            }
            
        except Exception as e:
            logger.error(f"Error getting opening range for {symbol}: {e}")
            return None

# Global instance
intraday_data = IntradayDataProvider()
