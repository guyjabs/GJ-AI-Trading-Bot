import yfinance as yf
import time
import pandas as pd
from src.utils import logger
from src.indicators import compute_sma

class MacroAnalyst:
    """
    Analyzes macroeconomic data (VIX, SPY trend, TNX) to determine the market regime.
    """
    def __init__(self):
        self.tickers = {
            'VIX': '^VIX',
            'TNX': '^TNX',
            'DXY': 'DX-Y.NYB',
            'SPY': 'SPY'
        }
        self._cache = None
        self._cache_time = 0
        self._cache_ttl = 1800  # 30 minutes

    def analyze_macro_context(self):
        now = time.time()
        if self._cache and (now - self._cache_time < self._cache_ttl):
            return self._cache

        try:
            # Download enough data for 50-day SMA
            data = yf.download(
                [self.tickers['VIX'], self.tickers['TNX'], self.tickers['SPY']], 
                period="60d", 
                progress=False
            )
            
            # Default fallback values
            vix_current = 20.0
            spy_trend = "FLAT"
            spy_vs_sma50_pct = 0.0
            tnx_yield = 4.0
            
            if not data.empty and 'Close' in data:
                if self.tickers['VIX'] in data['Close']:
                    vix_series = data['Close'][self.tickers['VIX']].dropna()
                    if not vix_series.empty:
                        vix_current = float(vix_series.iloc[-1])

                if self.tickers['TNX'] in data['Close']:
                    tnx_series = data['Close'][self.tickers['TNX']].dropna()
                    if not tnx_series.empty:
                        tnx_yield = float(tnx_series.iloc[-1])

                if self.tickers['SPY'] in data['Close']:
                    spy_series = data['Close'][self.tickers['SPY']].dropna()
                    if len(spy_series) > 0:
                        spy_current = float(spy_series.iloc[-1])
                        
                        # Use compute_sma instead of manual
                        sma50 = compute_sma(spy_series, period=50)
                        if not sma50.empty and not pd.isna(sma50.iloc[-1]):
                            spy_sma = float(sma50.iloc[-1])
                            spy_vs_sma50_pct = (spy_current - spy_sma) / spy_sma
                            
                            if spy_vs_sma50_pct > 0.01:
                                spy_trend = "UP"
                            elif spy_vs_sma50_pct < -0.01:
                                spy_trend = "DOWN"
                        else:
                            # Fallback if not enough data for SMA50
                            if spy_current > spy_series.iloc[0]:
                                spy_trend = "UP"
                            else:
                                spy_trend = "DOWN"

            # Regime Logic
            regime = "NEUTRAL"
            regime_numeric = 0.0
            
            if vix_current < 20 and spy_trend == "UP":
                regime = "RISK_ON"
                regime_numeric = 1.0
            elif vix_current > 30 or spy_trend == "DOWN":
                regime = "RISK_OFF"
                regime_numeric = -1.0
            elif 20 <= vix_current <= 25:
                regime = "CAUTIOUS"
                regime_numeric = -0.5
                
            result = {
                'regime': regime,
                'vix': vix_current,
                'spy_trend': spy_trend,
                'spy_vs_sma50_pct': spy_vs_sma50_pct,
                'tnx_yield': tnx_yield,
                'regime_numeric': regime_numeric
            }
            
            self._cache = result
            self._cache_time = now
            return result
            
        except Exception as e:
            logger.error(f"Macro Analyst Error: {e}")
            return {
                'regime': 'NEUTRAL', 
                'vix': 20.0, 
                'spy_trend': 'FLAT', 
                'spy_vs_sma50_pct': 0.0,
                'tnx_yield': 4.0,
                'regime_numeric': 0.0,
                'error': str(e)
            }
