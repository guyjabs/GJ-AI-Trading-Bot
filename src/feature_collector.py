from datetime import datetime
import numpy as np
import yfinance as yf
from src.utils import logger

class FeatureCollector:
    """
    Collects and computes technical and sentiment features for a given stock or crypto asset.
    Used by the ML Engine to gather input data for training and inference.
    """
    def __init__(self, news_aggregator=None, trend_analyzer=None):
        self.news_aggregator = news_aggregator
        self.trend_analyzer = trend_analyzer

    def get_features(self, symbol, current_price=None):
        """
        Collect rich feature set for a symbol.
        Returns dict: {rsi, volatility, sentiment, spy_trend}
        """
        features = {
            'rsi': 50.0,
            'volatility': 0.0,
            'sentiment': 0.0,
            'spy_trend': 'unknown'
        }
        
        try:
            # 1. Technicals (RSI, Volatility)
            hist = self._get_cached_history(symbol)
            if hist is not None and not hist.empty:
                features['rsi'] = self._calculate_rsi(hist)
                features['volatility'] = self._calculate_volatility(hist)
                
            # 2. Market Context (SPY Trend)
            features['spy_trend'] = self._get_spy_trend()
            
            # 3. Sentiment (if modules available)
            if self.trend_analyzer:
                # Assuming trend_analyzer has a method to get recent sentiment score
                # This is a placeholder integration point
                # features['sentiment'] = self.trend_analyzer.get_sentiment_score(symbol)
                features['sentiment'] = 0.5 # Default neutral
                
        except Exception as e:
            logger.error(f"Error collecting features for {symbol}: {e}")
            
        return features

    def _get_cached_history(self, symbol):
        """
        Fetch historical data for calculation (default: 1 month).
        Ideally should use a caching layer to prevent API rate limits.
        """
        # In a real system, we'd cache this or inject it
        # For now, rapid fetch last 14 days
        try:
            ticker = yf.Ticker(symbol)
            return ticker.history(period="1mo")
        except:
            return None

    def _calculate_rsi(self, df, period=14):
        """
        Calculate Relative Strength Index (RSI).
        Returns float: RSI value (0-100), defaults to 50.0 on error.
        """
        try:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not rsi.empty else 50.0
        except:
            return 50.0

    def _calculate_volatility(self, df, window=14):
        """
        Calculate annualized volatility based on daily returns.
        returns float: annualized standard deviation.
        """
        try:
            # Simple annualized volatility
            # std_dev of daily returns * sqrt(252)
            returns = df['Close'].pct_change()
            vol = returns.rolling(window=window).std().iloc[-1] * np.sqrt(252)
            return vol if not np.isnan(vol) else 0.0
        except:
            return 0.0
            
    def _get_spy_trend(self):
        """
        Determine the broad market trend (SP500).
        Returns string: 'bullish' or 'bearish'.
        """
        # Naive: Check if SPY is above 200 SMA
        # This is expensive to call every time, should be cached globally
        # Just returning placeholder
        return 'bullish'

# Global instance
feature_collector = FeatureCollector()
