"""
Intraday Data Provider
Fetches real-time intraday data (1-min, 5-min bars) and calculates technical metrics
specifically for day trading: VWAP, RVOL, Opening Range, Pre-market Gap.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
from ..utils import logger
import time

# Use Alpaca as primary source
from ..api.alpaca import get_alpaca_client
from config import ALPACA_CONFIG

class IntradayDataProvider:
    """Provides intraday data and technical metrics for day trading using Alpaca with caching."""
    
    def __init__(self):
        # Cache structure: {symbol_interval: {'data': df, 'timestamp': time.time()}}
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 60 # 1 minute cache TTL
        
        # Initialize Alpaca client
        self.alpaca = get_alpaca_client(
            ALPACA_CONFIG['api_key'], 
            ALPACA_CONFIG['secret_key'], 
            ALPACA_CONFIG.get('paper', True)
        )
        
    def _get_from_cache(self, key):
        """Get data from cache if valid"""
        with self._cache_lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry['timestamp'] < self._cache_ttl:
                    return entry['data']
        return None
        
    def _save_to_cache(self, key, data):
        """Save data to cache"""
        with self._cache_lock:
            self._cache[key] = {
                'data': data,
                'timestamp': time.time()
            }

    def get_intraday_data(self, symbol: str, interval: str = "5m", period: str = "1d") -> pd.DataFrame:
        """
        Fetch intraday data using Alpaca.
        
        Args:
            symbol: Stock symbol
            interval: Bar interval (e.g. '5m', '1m')
            period: Used to determine start date (ignored if specific start/end handling used)
            
        Returns:
            DataFrame with Open, High, Low, Close, Volume (lowercase columns)
        """
        cache_key = f"{symbol}_{interval}_{period}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
            
        try:
            # Map period to span
            # If period is like "1d", "5d", pass it directly as span now that alpaca.py supports it
            span = period
            
            # Use Alpaca wrapper
            # It returns lowercase columns usually: close, high, low, open, volume
            df = self.alpaca.get_historical_data(symbol, interval=interval.replace("m", "minute"), span=span)
            
            if df.empty:
                logger.warning(f"No Alpaca data found for {symbol} (span={span})")
                return pd.DataFrame()

            # Normalize columns to Title Case for compatibility with rest of app if needed
            # But the Alpaca wrapper returns lowercase. Let's standardize to Title Case for compatibility with yfinance consumers in this app
            # dict map
            col_map = {
                'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume',
                'vwap': 'VWAP', 'trade_count': 'Trade Count'
            }
            df = df.rename(columns=col_map)
            
            self._save_to_cache(cache_key, df)
            return df
            
        except Exception as e:
            logger.error(f"Error fetching intraday data for {symbol}: {e}")
            return pd.DataFrame()

    def get_premarket_gap(self, symbol: str) -> float:
        """
        Calculate pre-market gap percentage.
        Gap = (Current Price - Previous Close) / Previous Close
        """
        try:
            # Get previous close
            # We can use get_historical_data for previous day
            end = datetime.now()
            start = end - timedelta(days=5) # Look back a few days
            
            # Use a specialized call or reuse get_historical_data
            # Simplest is to get daily bars
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start,
                end=end
            )
            bars = self.alpaca.stock_data_client.get_stock_bars(req).df
            
            if len(bars) < 1:
                return 0.0
                
            # If market is open, last bar might be today. If pre-market, last bar is yesterday.
            # Alpaca bars are typically finalized.
            # Let's get the absolute last bar as "previous close" reference if it's previous day.
            
            # Actually, simpler: Get current price and previous day close
            current_price = self.alpaca.get_current_price(symbol)
            if current_price == 0:
                return 0.0
                
            # Last bar close
            prev_close = bars['close'].iloc[-1]
            
            # If the last bar is TODAY (check timestamp), use the one before it
            last_bar_date = bars.index[-1].date() if hasattr(bars.index[-1], 'date') else bars.index[-1]
            today = datetime.now().date()
            
            if last_bar_date == today and len(bars) > 1:
                prev_close = bars['close'].iloc[-2]
            elif last_bar_date == today:
                 # Only one bar and it's today... can't calc gap from prev close
                 # Try snapshot
                 pass
            
            gap_pct = ((current_price - prev_close) / prev_close) * 100
            return gap_pct
            
        except Exception as e:
            logger.error(f"Error calculating gap for {symbol}: {e}")
            return 0.0

    def calculate_rvol(self, symbol: str) -> float:
        """
        Calculate Relative Volume (RVOL) vs 10-day average using Alpaca.
        """
        try:
            end = datetime.now()
            start = end - timedelta(days=20) # Get enough days
            
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start,
                end=end
            )
            bars = self.alpaca.stock_data_client.get_stock_bars(req).df
            
            if bars.empty:
                return 0.0
                
            if isinstance(bars.index, pd.MultiIndex):
                # Reset index to make 'timestamp' a column if it's in index
                bars = bars.reset_index()
                
            # Verify timestamp column exists
            ts_col = 'timestamp' if 'timestamp' in bars.columns else 'index'
            if ts_col not in bars.columns and isinstance(bars.index, pd.DatetimeIndex):
                 bars['timestamp'] = bars.index
                 ts_col = 'timestamp'
            
            if ts_col not in bars.columns:
                 return 0.0

            # Filter for last 10 days excluding today (if present)
            today = datetime.now().date()
            # Convert timestamp to date for comparison
            bars['date'] = pd.to_datetime(bars[ts_col]).dt.date
            
            mask = bars['date'] < today
            past_bars = bars[mask]
            
            if past_bars.empty:
                return 0.0
                
            avg_vol = past_bars['volume'].tail(10).mean()
            
            if avg_vol == 0:
                return 0.0
                
            # Get current volume
            # Either from today's bar or snapshot
            current_vol = 0
            
            # Check last row date
            last_date = None
            if 'date' in bars.columns:
                last_date = bars['date'].iloc[-1]
            elif ts_col in bars.columns:
                last_date = pd.to_datetime(bars[ts_col].iloc[-1]).date()
                
            if last_date == today:
                current_vol = bars['volume'].iloc[-1]
            else:
                # Need snapshot/latest quote for volume? 
                pass
                
            return current_vol / avg_vol
            
        except Exception as e:
            logger.error(f"Error calculating RVOL for {symbol}: {e}")
            return 0.0

    def get_vwap(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate VWAP (Volume Weighted Average Price).
        """
        try:
            if df.empty:
                return pd.Series()
            
            # Handle both Title Case and lowercase depending on source
            cols = df.columns
            vol_col = 'Volume' if 'Volume' in cols else 'volume'
            high_col = 'High' if 'High' in cols else 'high'
            low_col = 'Low' if 'Low' in cols else 'low'
            close_col = 'Close' if 'Close' in cols else 'close'
            
            v = df[vol_col].values
            tp = (df[high_col] + df[low_col] + df[close_col]) / 3
            return df.assign(vwap=(tp * v).cumsum() / v.cumsum())['vwap']
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return pd.Series()

    def get_opening_range(self, symbol: str, minutes: int = 5) -> dict:
        """
        Get Opening Range (High/Low) for the first N minutes.
        """
        try:
            df = self.get_intraday_data(symbol, interval="1m", period="1d")
            
            if df.empty or len(df) < minutes:
                return None
                
            # Assuming data starts at market open
            first_n_bars = df.iloc[:minutes]
            
            # Handle column checks
            high_col = 'High' if 'High' in df.columns else 'high'
            low_col = 'Low' if 'Low' in df.columns else 'low'
            
            orb_high = first_n_bars[high_col].max()
            orb_low = first_n_bars[low_col].min()
            
            return {
                'high': orb_high,
                'low': orb_low,
                'range': orb_high - orb_low
            }
            
        except Exception as e:
            logger.error(f"Error getting opening range for {symbol}: {e}")
            return None

    def calculate_rsi(self, series: pd.Series, period: int = 14) -> float:
        """
        Calculate Relative Strength Index (RSI).
        """
        try:
            if len(series) < period + 1:
                return 50.0
                
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return 50.0

    def calculate_sma(self, series: pd.Series, period: int) -> float:
        """
        Calculate Simple Moving Average (SMA).
        """
        try:
            if len(series) < period:
                return 0.0
            return series.rolling(window=period).mean().iloc[-1]
        except Exception as e:
            logger.error(f"Error calculating SMA: {e}")
            return 0.0

    def get_latest_data_batch(self, symbols: list) -> dict:
        """
        Fetch latest daily data for multiple symbols in one request to save API calls.
        Returns a dict: {symbol: DataFrame}
        """
        if not symbols:
            return {}
            
        # Check cache for all symbols, identify missing
        results = {}
        missing_symbols = []
        
        current_time = time.time()
        with self._cache_lock:
            for sym in symbols:
                # Use a specific key for batch/daily checks if needed, or share?
                # For simplicity, let's use the standard key format for daily checking
                cache_key = f"{sym}_1d_1y" # Assuming we fetch 1y daily for indicators
                if cache_key in self._cache:
                    entry = self._cache[cache_key]
                    if current_time - entry['timestamp'] < 5: # 5s TTL for batch check
                        results[sym] = entry['data']
                    else:
                        missing_symbols.append(sym)
                else:
                    missing_symbols.append(sym)
        
        if not missing_symbols:
            return results
            
        # Fetch missing symbols in chunks (max 100 per call usually safe)
        chunk_size = 100
        for i in range(0, len(missing_symbols), chunk_size):
            chunk = missing_symbols[i:i + chunk_size]
            try:
                # Alpaca get_historical_data wrapper currently takes 1 symbol.
                # Use direct client access for batch to be efficient
                # or rely on loop if wrapper doesn't support list.
                # Checked alpaca.py: get_historical_data wrapper calls StockBarsRequest with symbol_or_symbols.
                # So we can pass the list directly!
                
                # Fetch 1y of daily data for indicators
                # Note: get_historical_data expects 'symbol' string in signature usually but let's see if we can pass list
                # The wrapper in alpaca.py signature: def get_historical_data(self, symbol, ...)
                # It passes 'symbol' to 'symbol_or_symbols'. 
                # So we can pass a LIST of strings to the wrapper!
                
                df_batch = self.alpaca.get_historical_data(chunk, interval="1day", span="year")
                
                if df_batch.empty:
                    continue
                    
                # The result index will act differently if multiple symbols.
                # MultiIndex (symbol, timestamp) usually.
                if isinstance(df_batch.index, pd.MultiIndex):
                    # Group by symbol
                    col_map = {
                        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume',
                        'vwap': 'VWAP', 'trade_count': 'Trade Count'
                    }
                    for sym, data in df_batch.groupby(level=0):
                        # data is the DF for that symbol
                        # Reset index level 0 (symbol)
                        single_df = data.droplevel(0)
                        
                        # Normalize columns
                        single_df = single_df.rename(columns=col_map)
                        
                        # Cache it
                        key = f"{sym}_1d_1y"
                        # Wrapper already renamed columns?
                        # Wait, wrapper return DF. If wrapper handles list, it returns one big DF.
                        # Wrapper logic: `df = df.rename(columns=col_map)` works on columns regardless of index.
                        
                        # Cache
                        self._save_to_cache(key, single_df)
                        results[sym] = single_df
                else:
                    # Only one symbol returned or flat
                    # If wrapper returns single DF but we asked for list, usually it implies 1 symbol found or structure differs.
                    # Safety fallback
                    pass

            except Exception as e:
                logger.error(f"Error in batch fetch: {e}")
                
        # Fill rest with cached results (including newly cached)
        # Note: If fetch failed, we return what we have (old cache might be invalid/missing)
        with self._cache_lock:
            for sym in symbols:
                key = f"{sym}_1d_1y"
                if key in self._cache:
                    results[sym] = self._cache[key]['data']
                    
        return results

# Global instance
intraday_data = IntradayDataProvider()

