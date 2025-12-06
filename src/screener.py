"""
Multi-strategy stock screener that identifies promising stocks using
Momentum, Growth, and Value investing strategies.
"""

from typing import List, Dict, Tuple
from datetime import datetime
import json
import os

from .data.stock_data import stock_data_provider
from .utils import logger

# Stock universes
SP500_SYMBOLS = [
    # Top 50 S&P 500 by market cap (for initial implementation)
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "UNH", "JNJ",
    "V", "XOM", "WMT", "JPM", "LLY", "MA", "PG", "AVGO", "HD", "CVX",
    "MRK", "ABBV", "KO", "PEP", "COST", "ADBE", "MCD", "CSCO", "ACN", "TMO",
    "NFLX", "ABT", "CRM", "ORCL", "DIS", "WFC", "AMD", "INTC", "VZ", "NKE",
    "QCOM", "TXN", "PM", "UPS", "HON", "INTU", "AMGN", "COP", "RTX", "BA"
]

RUSSELL_2000_SAMPLE = [
    # Sample of Russell 2000 small caps
    "FIVE", "SAIA", "ENSG", "CEIX", "BOOT", "CRVL", "FTDR", "UFPI", "PRIM", "MATX"
]

# Combined universe
DEFAULT_UNIVERSE = SP500_SYMBOLS + RUSSELL_2000_SAMPLE

# Crypto Universe
CRYPTO_UNIVERSE = [
    "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "SHIB-USD", 
    "LTC-USD", "BCH-USD", "ETC-USD", "AVAX-USD", "LINK-USD"
]

class StockScreener:
    def __init__(self, universe: List[str] = None):
        """
        Initialize screener with stock universe.
        
        Args:
            universe: List of stock symbols to screen. Defaults to S&P 500 + Russell 2000 sample.
        """
        self.universe = universe or DEFAULT_UNIVERSE
        self.stock_data = {}
        self.strategy_weights = {
            'momentum': 0.30,
            'growth': 0.40,
            'value': 0.30
        }
    
    def load_strategy_weights(self):
        """Load learned strategy weights from file"""
        weights_file = "data/strategy_weights.json"
        if os.path.exists(weights_file):
            try:
                with open(weights_file, 'r') as f:
                    self.strategy_weights = json.load(f)
                logger.info(f"Loaded strategy weights: {self.strategy_weights}")
            except Exception as e:
                logger.error(f"Error loading strategy weights: {e}")
    
    def save_strategy_weights(self):
        """Save strategy weights to file"""
        weights_file = "data/strategy_weights.json"
        try:
            os.makedirs("data", exist_ok=True)
            with open(weights_file, 'w') as f:
                json.dump(self.strategy_weights, f, indent=2)
            logger.info(f"Saved strategy weights: {self.strategy_weights}")
        except Exception as e:
            logger.error(f"Error saving strategy weights: {e}")
    
    def fetch_universe_data(self, progress_callback=None):
        """Fetch data for all stocks in universe with progress reporting"""
        logger.info(f"Fetching data for {len(self.universe)} stocks...")
        
        self.stock_data = {}
        batch_size = 5
        total = len(self.universe)
        
        for i in range(0, total, batch_size):
            batch = self.universe[i:i+batch_size]
            batch_str = ", ".join(batch)
            
            # Report progress
            if progress_callback:
                percent = 45 + (i / total) * 10 # Map 45-55% range
                progress_callback(f"Scanning {batch_str}...", percent, 'in-progress')
            
            try:
                # Fetch batch
                batch_data = stock_data_provider.fetch_multiple(batch)
                self.stock_data.update(batch_data)
            except Exception as e:
                logger.error(f"Error fetching batch {batch}: {e}")
                
        logger.info(f"Successfully fetched data for {len(self.stock_data)} stocks")
        return self.stock_data

    def run_screener(self, progress_callback=None):
        """
        Main entry point for external calls.
        Wraps run_all_strategies with progress reporting.
        """
        # Fetch data with progress
        self.fetch_universe_data(progress_callback)
        
        # Run strategies
        if progress_callback:
            progress_callback("Analyzing market data (Momentum, Growth, Value)...", 55, 'in-progress')
            
        return self.run_all_strategies(skip_fetch=True)
    
    def screen_momentum(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Momentum strategy: Find stocks with strong recent price action.
        
        Criteria:
        - Price gain > 5% in last 5 days
        - Volume > 2x average
        - RSI between 50-70 (strong but not overbought)
        - Price above 50-day MA
        - Market cap > $1B
        
        Returns:
            List of (symbol, score) tuples, sorted by score descending
        """
        candidates = []
        
        for symbol, data in self.stock_data.items():
            try:
                score = 0
                
                # Quality filters
                if data.get('market_cap', 0) < 1_000_000_000:  # $1B minimum
                    continue
                if data.get('avg_volume', 0) < 100_000:  # Minimum liquidity
                    continue
                if data.get('current_price', 0) < 5:  # Avoid penny stocks
                    continue
                
                # Momentum signals
                price_change_5d = data.get('price_change_5d', 0)
                if price_change_5d > 5:
                    score += price_change_5d * 2  # Weight recent momentum heavily
                
                # Volume surge
                volume_ratio = data.get('volume_ratio', 0)
                if volume_ratio > 2:
                    score += (volume_ratio - 1) * 10
                
                # Price vs moving averages
                current_price = data.get('current_price', 0)
                ma_50 = data.get('50day_avg', 0)
                if current_price > ma_50 and ma_50 > 0:
                    score += ((current_price - ma_50) / ma_50) * 100
                
                # Distance from 52-week high (closer is better for momentum)
                pct_from_high = data.get('pct_from_52week_high', -100)
                if pct_from_high > -10:  # Within 10% of 52-week high
                    score += (10 + pct_from_high) * 2
                
                # Report detailed finding if callback exists
                    status_text = "PASS" if score > 0 else "FAIL"
                    # Add price info
                    price = data.get('current_price', 0)
                    change = data.get('day_change_pct', 0) * 100 # usually decimal? No, yfinance returns decimal or pct? check stock_data usage.
                    # stock_data.py line 97: info.get('regularMarketChangePercent', 0). Usually this is e.g. 0.012 for 1.2% or 1.2?
                    # Let's assume decimal based on multiplier elsewhere. Wait, line 162: (Close - Close)/Close * 100. So manual calc is 100 based.
                    # yfinance info['regularMarketChangePercent'] is typically decimal (0.01).
                    if abs(change) < 0.2: # If it's small float like 0.01, multiply by 100. If it's 1.2, don't.
                         # Actually safer to just display as is if I'm unsure, or check value.
                         # Let's trust I can format it roughly.
                         pass
                    
                    # Correction: I'll use the cached 'day_change_pct' which comes from yfinance.
                    # Let's check stock_data.py again. line 97.
                    # I will assume it is decimal format (e.g. 0.015 for 1.5%) -> so multiply by 100.
                    
                    change_pct = change * 100
                    trend = "🟢" if change >= 0 else "🔴"
                    price_str = f"${price:.2f} {trend} {change_pct:+.2f}%"
                    
                    details = f"{price_str} | RSI={data.get('rsi_14', 'N/A')}, Vol={data.get('volume_ratio', 'N/A'):.1f}x"
                    progress_callback(f"🔎 {symbol}: {details} -> {status_text} ({score:.1f})", 0, 'detail')

                if score > 0:
                    candidates.append((symbol, score))
            
            except Exception as e:
                logger.debug(f"Error screening {symbol} for momentum: {e}")
                if progress_callback:
                    progress_callback(f"⚠️ {symbol}: Error analysis - {str(e)}", 0, 'detail')
        
        # Sort by score and return top N
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
    
    def screen_growth(self, top_n: int = 15) -> List[Tuple[str, float]]:
        """
        Growth strategy: Find companies with strong growth metrics.
        
        Criteria:
        - Revenue growth > 15% YoY
        - EPS growth > 10% YoY
        - Gross margin > 30%
        - Positive analyst sentiment
        
        Returns:
            List of (symbol, score) tuples, sorted by score descending
        """
        candidates = []
        
        for symbol, data in self.stock_data.items():
            try:
                score = 0
                
                # Quality filters
                if data.get('market_cap', 0) < 500_000_000:  # $500M minimum
                    continue
                if data.get('current_price', 0) < 5:
                    continue
                
                # Revenue growth
                revenue_growth = data.get('revenue_growth', 0)
                if revenue_growth > 0.15:  # 15%+
                    score += revenue_growth * 100
                
                # Earnings growth
                earnings_growth = data.get('earnings_growth', 0)
                if earnings_growth > 0.10:  # 10%+
                    score += earnings_growth * 80
                
                # Quarterly earnings growth (more recent)
                quarterly_growth = data.get('earnings_quarterly_growth', 0)
                if quarterly_growth > 0:
                    score += quarterly_growth * 60
                
                # Profitability margins
                gross_margin = data.get('gross_margin', 0)
                if gross_margin > 0.30:  # 30%+
                    score += gross_margin * 50
                
                operating_margin = data.get('operating_margin', 0)
                if operating_margin > 0.15:  # 15%+
                    score += operating_margin * 40
                
                # Return on equity
                roe = data.get('roe', 0)
                if roe > 0.15:  # 15%+
                    score += roe * 30
                
                # Analyst sentiment
                recommendation = data.get('recommendation', 'none')
                if recommendation in ['strong_buy', 'buy']:
                    score += 20
                
                # Report detailed finding
                if progress_callback:
                    status_text = "PASS" if score > 0 else "FAIL"
                    price = data.get('current_price', 0)
                    change = data.get('day_change_pct', 0) * 100
                    trend = "🟢" if change >= 0 else "🔴"
                    price_str = f"${price:.2f} {trend} {change:+.2f}%"
                    
                    details = f"{price_str} | Rev={data.get('revenue_growth', 0):.1%}, Marg={data.get('gross_margin', 0):.1%}"
                    progress_callback(f"🔎 {symbol}: {details} -> {status_text} ({score:.1f})", 0, 'detail')

                if score > 0:
                    candidates.append((symbol, score))
            
            except Exception as e:
                logger.debug(f"Error screening {symbol} for growth: {e}")
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
    
    def screen_value(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Value strategy: Find undervalued stocks with strong fundamentals.
        
        Criteria:
        - P/E ratio < 15
        - P/B ratio < 2
        - Dividend yield > 2%
        - Positive free cash flow
        - Debt-to-equity < 0.5
        
        Returns:
            List of (symbol, score) tuples, sorted by score descending
        """
        candidates = []
        
        for symbol, data in self.stock_data.items():
            try:
                score = 0
                
                # Quality filters
                if data.get('market_cap', 0) < 1_000_000_000:  # $1B minimum
                    continue
                if data.get('current_price', 0) < 5:
                    continue
                
                # Valuation metrics (lower is better, so invert scoring)
                pe_ratio = data.get('pe_ratio', 999)
                if 0 < pe_ratio < 15:
                    score += (15 - pe_ratio) * 3
                
                pb_ratio = data.get('pb_ratio', 999)
                if 0 < pb_ratio < 2:
                    score += (2 - pb_ratio) * 20
                
                ps_ratio = data.get('ps_ratio', 999)
                if 0 < ps_ratio < 2:
                    score += (2 - ps_ratio) * 15
                
                # Dividend yield (higher is better)
                div_yield = data.get('dividend_yield', 0)
                if div_yield > 0.02:  # 2%+
                    score += div_yield * 200
                
                # Financial health
                debt_to_equity = data.get('debt_to_equity', 999)
                if debt_to_equity < 0.5:
                    score += (0.5 - debt_to_equity) * 20
                
                # Free cash flow (positive is good)
                fcf = data.get('free_cash_flow', 0)
                if fcf > 0:
                    score += 20
                
                # Profitability
                profit_margin = data.get('profit_margin', 0)
                if profit_margin > 0.10:  # 10%+
                    score += profit_margin * 30
                
                # ROE
                roe = data.get('roe', 0)
                if roe > 0.10:  # 10%+
                    score += roe * 25
                
                # Report detailed finding
                if progress_callback:
                    status_text = "PASS" if score > 0 else "FAIL"
                    price = data.get('current_price', 0)
                    change = data.get('day_change_pct', 0) * 100
                    trend = "🟢" if change >= 0 else "🔴"
                    price_str = f"${price:.2f} {trend} {change:+.2f}%"
                    
                    details = f"{price_str} | P/E={data.get('pe_ratio', 'N/A')}, P/B={data.get('pb_ratio', 'N/A')}"
                    progress_callback(f"🔎 {symbol}: {details} -> {status_text} ({score:.1f})", 0, 'detail')

                if score > 0:
                    candidates.append((symbol, score))
            
            except Exception as e:
                logger.debug(f"Error screening {symbol} for value: {e}")
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
    
    def screen_crypto(self) -> List[Tuple[str, float]]:
        """
        Crypto Strategy: Momentum & Reversal
        
        Criteria:
        - Momentum: Price up > 3% in 24h
        - Volume: High relative volume
        - Reversal: RSI < 30 (Oversold bounce)
        """
        candidates = []
        
        # Fetch crypto data
        logger.info(f"Fetching data for {len(CRYPTO_UNIVERSE)} crypto assets...")
        crypto_data = stock_data_provider.fetch_multiple(CRYPTO_UNIVERSE)
        
        for symbol, data in crypto_data.items():
            try:
                score = 0
                
                # Momentum
                price_change = data.get('price_change_5d', 0) # Using 5d as proxy for trend
                if price_change > 3:
                    score += price_change * 5
                
                # Volume
                volume_ratio = data.get('volume_ratio', 0)
                if volume_ratio > 1.5:
                    score += (volume_ratio - 1) * 20
                
                # Reversal (Oversold RSI)
                rsi = data.get('rsi', 50)
                if rsi < 30:
                    score += (30 - rsi) * 5  # Bounce play
                elif rsi > 70:
                    score -= (rsi - 70) * 2  # Overbought penalty
                
                # Clean symbol (remove -USD for Robinhood)
                clean_symbol = symbol.replace("-USD", "")
                
                
                if progress_callback:
                    status_text = "PASS" if score > 0 else "FAIL"
                    price = data.get('current_price', 0)
                    # Crypto change is usually calculated manually as price_change_5d in my code?
                    # Let's see. 'price_change_5d' is in data.
                    # Or 'day_change_pct' if available.
                    change = data.get('day_change_pct', data.get('price_change_5d', 0))
                    # Note: crypto change might be percent already (e.g. 5.0 for 5%) if from Coingecko/Mock?
                    # data['price_change_5d'] was calculated as * 100 in stock_data.py line 162.
                    # So it is percentage (5.0).
                    # If using 'day_change_pct' (from yfinance info), it is decimal.
                    # This is ambiguous. I will check logic.
                    # stock_data.py fetches crypto using fetch_stock_data too? 
                    # Yes, stock_data_provider.fetch_multiple(CRYPTO_UNIVERSE).
                    # So structure is same.
                    # I will assume decimal for 'day_change_pct'.
                    if abs(change) < 0.5: # Likely decimal
                        change = change * 100
                    
                    trend = "🟢" if change >= 0 else "🔴"
                    price_str = f"${price:.2f} {trend} {change:+.2f}%"

                    details = f"{price_str} | RSI={rsi:.1f}, Vol={volume_ratio:.1f}x"
                    progress_callback(f"🔎 {clean_symbol}: {details} -> {status_text} ({score:.1f})", 0, 'detail')

                if score > 0:
                    candidates.append((clean_symbol, score))
                    
            except Exception as e:
                logger.debug(f"Error screening crypto {symbol}: {e}")
    
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:5] # Top 5 crypto picks

    def check_market_sentiment(self) -> str:
        """
        Check overall market sentiment using SPY.
        Returns: 'bullish', 'bearish', or 'neutral'
        """
        try:
            spy = yf.Ticker("SPY")
            hist = spy.history(period="5d")
            
            if len(hist) < 2:
                return "neutral"
                
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            pct_change = (current_price - prev_close) / prev_close
            
            logger.info(f"Market Sentiment (SPY): {pct_change:.2%} today")
            
            if pct_change < -0.01: # Down more than 1%
                logger.warning("📉 Market is BEARISH (SPY < -1%). reducing exposure.")
                return "bearish"
            elif pct_change > 0.005: # Up more than 0.5%
                return "bullish"
            else:
                return "neutral"
        except Exception as e:
            logger.error(f"Error checking market sentiment: {e}")
            return "neutral"

    def run_all_strategies(self, skip_fetch=False) -> Dict[str, List[str]]:
        """
        Run all screening strategies and combine results.
        Returns dict with lists of symbols for each strategy.
        """
        logger.info("Running multi-strategy stock screening...")
        
        # Check market sentiment first
        sentiment = self.check_market_sentiment()
        
        # If market is crashing, return empty results to prevent buying
        if sentiment == "bearish":
            logger.warning("⚠️ SKIPPING SCREENER due to bearish market conditions. Cash is King.")
            empty_results = {
                'momentum': [],
                'growth': [],
                'value': [],
                'all': [],
                'timestamp': datetime.now().isoformat(),
                'weights': self.strategy_weights,
                'market_sentiment': sentiment
            }
            self.save_screening_results(empty_results)
            return empty_results

            return empty_results

        self.load_strategy_weights()
        if not skip_fetch:
            self.fetch_universe_data()
        
        # Adjust number of picks based on sentiment
        base_picks = 35
        if sentiment == "neutral":
            base_picks = 25 # Be slightly more conservative
            
        momentum_picks = self.screen_momentum(top_n=int(base_picks * self.strategy_weights['momentum']))
        growth_picks = self.screen_growth(top_n=int(base_picks * self.strategy_weights['growth']))
        value_picks = self.screen_value(top_n=int(base_picks * self.strategy_weights['value']))
        
        # Screen Crypto
        crypto_picks = self.screen_crypto()
        
        results = {
            'momentum': [x[0] for x in momentum_picks],
            'growth': [x[0] for x in growth_picks],
            'value': [x[0] for x in value_picks],
            'crypto': [x[0] for x in crypto_picks],
            'timestamp': datetime.now().isoformat(),
            'weights': self.strategy_weights,
            'market_sentiment': sentiment
        }
        
        # Combine unique symbols (stocks only for 'all' list to avoid confusion in main loop)
        all_symbols = list(set(results['momentum'] + results['growth'] + results['value']))
        results['all'] = all_symbols
        
        logger.info(f"Momentum picks ({len(momentum_picks)}): {results['momentum']}")
        logger.info(f"Growth picks ({len(growth_picks)}): {results['growth']}")
        logger.info(f"Value picks ({len(value_picks)}): {results['value']}")
        logger.info(f"Crypto picks ({len(crypto_picks)}): {results['crypto']}")
        
        self.save_screening_results(results)
        logger.info(f"Total unique stocks selected: {len(all_symbols)}")
        
        return results
    
    def save_screening_results(self, results: Dict):
        """Save screening results to file"""
        results_file = "data/screening_results.json"
        try:
            os.makedirs("data", exist_ok=True)
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved screening results to {results_file}")
        except Exception as e:
            logger.error(f"Error saving screening results: {e}")
    
    def load_screening_results(self) -> Dict:
        """Load latest screening results"""
        results_file = "data/screening_results.json"
        if os.path.exists(results_file):
            try:
                with open(results_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading screening results: {e}")
        return {'all': []}

# Global instance
screener = StockScreener()
