"""
Stock data module for fetching and caching fundamental and technical data.
Uses yfinance for data retrieval and implements caching to avoid API limits.
"""

import yfinance as yf
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import concurrent.futures

from ..utils import logger

# Cache settings
CACHE_DIR = "data/cache"
CACHE_DURATION_HOURS = 24

class StockDataProvider:
    def __init__(self):
        self.cache = {}
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        """Create cache directory if it doesn't exist"""
        os.makedirs(CACHE_DIR, exist_ok=True)
    
    def get_cache_path(self, symbol: str) -> str:
        """Get cache file path for a symbol"""
        return os.path.join(CACHE_DIR, f"{symbol}.json")
    
    def is_cache_valid(self, symbol: str) -> bool:
        """Check if cached data is still valid"""
        cache_path = self.get_cache_path(symbol)
        if not os.path.exists(cache_path):
            return False
        
        # Check file age
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        age = datetime.now() - file_time
        return age < timedelta(hours=CACHE_DURATION_HOURS)
    
    def load_from_cache(self, symbol: str) -> Optional[Dict]:
        """Load data from cache"""
        try:
            cache_path = self.get_cache_path(symbol)
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Cache load failed for {symbol}: {e}")
            return None
    
    def save_to_cache(self, symbol: str, data: Dict):
        """Save data to cache"""
        try:
            cache_path = self.get_cache_path(symbol)
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.debug(f"Cache save failed for {symbol}: {e}")
    
    def fetch_stock_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch comprehensive stock data for a symbol.
        Returns dict with fundamental and technical data.
        """
        # Check cache first
        if self.is_cache_valid(symbol):
            cached_data = self.load_from_cache(symbol)
            if cached_data:
                logger.debug(f"Using cached data for {symbol}")
                return cached_data
        
        try:
            logger.debug(f"Fetching fresh data for {symbol}")
            ticker = yf.Ticker(symbol)
            
            # Get basic info
            info = ticker.info
            
            # Get historical data for technical indicators
            hist = ticker.history(period="1y")
            
            if hist.empty or not info:
                logger.debug(f"No data available for {symbol}")
                return None
            
            # Extract relevant data
            data = {
                'symbol': symbol,
                'fetched_at': datetime.now().isoformat(),
                
                # Price data
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'previous_close': info.get('previousClose', 0),
                'day_change_pct': info.get('regularMarketChangePercent', 0),
                
                # Volume
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0),
                'avg_volume_10day': info.get('averageVolume10days', 0),
                
                # Market cap and size
                'market_cap': info.get('marketCap', 0),
                'shares_outstanding': info.get('sharesOutstanding', 0),
                
                # Valuation ratios
                'pe_ratio': info.get('trailingPE', info.get('forwardPE', 0)),
                'pb_ratio': info.get('priceToBook', 0),
                'ps_ratio': info.get('priceToSalesTrailing12Months', 0),
                'peg_ratio': info.get('pegRatio', 0),
                
                # Growth metrics
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                'earnings_quarterly_growth': info.get('earningsQuarterlyGrowth', 0),
                
                # Profitability
                'profit_margin': info.get('profitMargins', 0),
                'operating_margin': info.get('operatingMargins', 0),
                'gross_margin': info.get('grossMargins', 0),
                'roe': info.get('returnOnEquity', 0),
                'roa': info.get('returnOnAssets', 0),
                
                # Financial health
                'debt_to_equity': info.get('debtToEquity', 0),
                'current_ratio': info.get('currentRatio', 0),
                'quick_ratio': info.get('quickRatio', 0),
                'free_cash_flow': info.get('freeCashflow', 0),
                'operating_cash_flow': info.get('operatingCashflow', 0),
                
                # Dividend
                'dividend_yield': info.get('dividendYield', 0),
                'payout_ratio': info.get('payoutRatio', 0),
                
                # Analyst data
                'target_price': info.get('targetMeanPrice', 0),
                'recommendation': info.get('recommendationKey', 'none'),
                'num_analyst_opinions': info.get('numberOfAnalystOpinions', 0),
                
                # Technical indicators (calculated from history)
                '52week_high': info.get('fiftyTwoWeekHigh', 0),
                '52week_low': info.get('fiftyTwoWeekLow', 0),
                '50day_avg': info.get('fiftyDayAverage', 0),
                '200day_avg': info.get('twoHundredDayAverage', 0),
                
                # Sector and industry
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
            }
            
            # Calculate additional metrics
            if data['current_price'] and data['52week_high']:
                data['pct_from_52week_high'] = ((data['current_price'] - data['52week_high']) / data['52week_high']) * 100
            
            if data['volume'] and data['avg_volume']:
                data['volume_ratio'] = data['volume'] / data['avg_volume'] if data['avg_volume'] > 0 else 0
            
            # Calculate price momentum (5-day, 20-day, 60-day)
            if len(hist) >= 5:
                data['price_change_5d'] = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100
            if len(hist) >= 20:
                data['price_change_20d'] = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-20]) / hist['Close'].iloc[-20]) * 100
            if len(hist) >= 60:
                data['price_change_60d'] = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-60]) / hist['Close'].iloc[-60]) * 100
            
            # Save to cache
            self.save_to_cache(symbol, data)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def fetch_multiple(self, symbols: List[str], delay: float = 0.1) -> Dict[str, Dict]:
        """
        Fetch data for multiple symbols in parallel.
        Returns dict mapping symbol to data.
        """
        results = {}
        total = len(symbols)
        
        # Use ThreadPoolExecutor for parallel processing
        # yfinance is IO bound, so threads work well
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Create a future for each symbol
            future_to_symbol = {executor.submit(self.fetch_stock_data, symbol): symbol for symbol in symbols}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_symbol)):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if data:
                        results[symbol] = data
                    logger.debug(f"Fetched {symbol} ({i+1}/{total})")
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
        
        return results
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cache for a symbol or all symbols"""
        if symbol:
            cache_path = self.get_cache_path(symbol)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                logger.info(f"Cleared cache for {symbol}")
        else:
            # Clear all cache
            for file in os.listdir(CACHE_DIR):
                if file.endswith('.json'):
                    os.remove(os.path.join(CACHE_DIR, file))
            logger.info("Cleared all cache")

# Global instance
stock_data_provider = StockDataProvider()
