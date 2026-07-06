"""
Multi-strategy stock screener that identifies promising stocks using
Momentum, Growth, and Value investing strategies.
"""

from typing import List, Dict, Tuple
from datetime import datetime
import json
import os
import yfinance as yf

from .data.stock_data import stock_data_provider
from .utils import logger
from .config_manager import config_manager
from .research.crypto_discoverer import crypto_discoverer
from .research.etoro_scraper import etoro_scraper

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
    "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", 
    "LTC/USD", "BCH/USD", "ETC/USD", "AVAX/USD", "LINK/USD"
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
        """Load learned strategy weights from DB"""
        from .data.db import db
        weights = db.load_latest_weights()
        if weights:
            self.strategy_weights = weights
            logger.info(f"Loaded strategy weights: {self.strategy_weights}")
        else:
            logger.info("Using default strategy weights (no DB record found)")
    
    def save_strategy_weights(self):
        """Save strategy weights to DB"""
        from .data.db import db
        db.save_weights(self.strategy_weights, reason="Screener Update")

    def log_strategy_decision(self, action: str, reason: str):
        """
        Log a strategy decision to DB.
        Currently mapping to strategy_weights table update or can be just a log.
        Since we don't have a dedicated 'decision log' table yet, we'll rely on logging 
        and only save weights if they changed.
        """
        # If action implies update, save weights with reason.
        if action == "updated":
            from .data.db import db
            db.save_weights(self.strategy_weights, reason=reason)
            logger.info(f"Logged strategy decision: {action} - {reason}")
        else:
            logger.info(f"Strategy decision: {action} - {reason}")
    
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

    def calculate_industry_averages(self) -> Dict[str, Dict]:
        """Calculate average metrics per industry for relative comparison"""
        industry_data = {}
        
        for symbol, data in self.stock_data.items():
            ind = data.get('industry', 'Unknown')
            if ind == 'Unknown': continue
            
            if ind not in industry_data:
                industry_data[ind] = {'pe': [], 'peg': [], 'fcf_share': []}
            
            # P/E
            pe = data.get('pe_ratio', 0)
            if pe > 0: industry_data[ind]['pe'].append(pe)
            
            # PEG
            peg = data.get('peg_ratio', 0)
            if peg > 0: industry_data[ind]['peg'].append(peg)
            
            # Cashflow per share (Free Cash Flow / Shares Outstanding)
            fcf = data.get('free_cash_flow', 0)
            shares = data.get('shares_outstanding', 0)
            if fcf and shares:
                industry_data[ind]['fcf_share'].append(fcf / shares)

        # Compute averages
        averages = {}
        for ind, metrics in industry_data.items():
            averages[ind] = {
                'avg_pe': sum(metrics['pe']) / len(metrics['pe']) if metrics['pe'] else 20,
                'avg_peg': sum(metrics['peg']) / len(metrics['peg']) if metrics['peg'] else 2,
                'avg_fcf_share': sum(metrics['fcf_share']) / len(metrics['fcf_share']) if metrics['fcf_share'] else 0
            }
        return averages

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
            
        return self.run_all_strategies(skip_fetch=True, progress_callback=progress_callback)
    
    def screen_momentum(self, top_n: int = 10, progress_callback=None) -> List[Tuple[str, float]]:
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
        metrics = config_manager.get_metrics().get('momentum', {})
        min_gain = metrics.get('min_top_gainers_pct', 5)
        min_rel_vol = metrics.get('min_volume_ratio', 1.5)
        
        for symbol, data in self.stock_data.items():
            try:
                score = 0
                
                # Quality filters
                market_cap = data.get('market_cap', 0)
                if market_cap < 1_000_000_000:  # $1B minimum
                    continue
                
                # DATA CHECK: Ensure volume is higher than average (Previous Month proxy)
                # We use volume_ratio which is Vol / AvgVol. If > 1.0, it's higher than average.
                volume_ratio = data.get('volume_ratio', 0)
                if volume_ratio <= 1.0: 
                    continue # Strict rule: Volume MUST be higher than average
                
                # Strict rule: Relative Volume > 1.5 (or config)
                if volume_ratio <= min_rel_vol:
                    continue

                if data.get('current_price', 0) < 5:  # Avoid penny stocks
                    continue
                
                # Momentum signals
                price_change_5d = data.get('price_change_5d', 0)
                
                # Strict rule: Price went up > 5% (or config)
                if price_change_5d < min_gain:
                    continue 

                # If passed filters, score it high!
                score += price_change_5d * 5
                score += (volume_ratio - 1) * 20
                
                # Price vs moving averages
                current_price = data.get('current_price', 0)
                ma_50 = data.get('50day_avg', 0)
                if current_price > ma_50 and ma_50 > 0:
                    score += ((current_price - ma_50) / ma_50) * 50
                
                # Distance from 52-week high (closer is better for momentum)
                pct_from_high = data.get('pct_from_52week_high', -100)
                if pct_from_high > -10:  # Within 10% of 52-week high
                    score += (10 + pct_from_high) * 2

                # RSI Check (Enabled)
                # target: 50-70 (strong trend but not overbought)
                rsi = data.get('rsi_14', 50)
                if 50 <= rsi <= 70:
                    score += 15  # Good momentum zone
                elif rsi > 70:
                    score -= (rsi - 70) * 1.5  # Overbought penalty
                elif rsi < 40:
                    score -= 10  # Too weak

                # Report detailed finding if callback exists
                if progress_callback:
                    status_text = "PASS" if score > 0 else "FAIL"
                    price = data.get('current_price', 0)
                    change = data.get('day_change_pct', 0) * 100 
                    trend = "🟢" if change >= 0 else "🔴"
                    price_str = f"${price:.2f} {trend} {change:+.2f}%"
                    
                    details = f"{price_str} | RSI={data.get('rsi_14', 'N/A')}, Vol={data.get('volume_ratio', 'N/A'):.1f}x"
                    progress_callback(f"🔎 {symbol}: {details} -> {status_text} ({score:.1f})", 0, 'detail')

                if score > 0:
                    candidates.append((symbol, score))
            
            except Exception as e:
                logger.debug(f"Error screening {symbol} for momentum: {e}")
        
        # Sort by score and return top N
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
    
    def screen_growth(self, top_n: int = 15, progress_callback=None) -> List[Tuple[str, float]]:
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
        metrics = config_manager.get_metrics().get('growth', {})
        trending_industries = metrics.get('trending_industries', [])
        min_earnings_growth = metrics.get('min_earnings_growth', 10) / 100.0  # Convert to decimal
        
        # Calculate industry average earnings growth
        industry_avgs = self.calculate_industry_averages()
        
        for symbol, data in self.stock_data.items():
            try:
                score = 0
                
                # INDUSTRY CHECK: Must be in specific industry list
                industry = data.get('industry', 'Unknown')
                if trending_industries and industry not in trending_industries:
                    # Optional: Strict exclude? Or just penalty?
                    # User said "focus on specific industries... Identify stocks in that industry"
                    # Let's STRICTLY filter for now, or just boost heavily.
                    # "Identified stocks in THAT industry" implies logic:
                    # 1. Filter by Trending Industry list -> 2. Find growth > peers
                    continue 

                # Quality filters
                if data.get('market_cap', 0) < 500_000_000:  # $500M minimum
                    continue
                if data.get('current_price', 0) < 5:
                    continue
                
                # Check for latest earnings showing growth (Revenue or Earnings)
                revenue_growth = data.get('revenue_growth', 0)
                earnings_growth = data.get('earnings_growth', 0)
                
                if earnings_growth <= min_earnings_growth and revenue_growth <= 0.10: 
                    continue # Needs some growth
                
                # Score based on growth
                score += (earnings_growth * 100) + (revenue_growth * 80)
                
                # Forecasted to grow more than peers?
                # We don't have explicit "forecast" data in this simple provider, using trailing/current growth as proxy.
                # Or use analyst target price?
                # Let's compare vs Industry Average growth if available, or just general relative score.
                
                score += 50 # Base score for making it through the industry filter
                
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
                    
                    details = f"{price_str} | Ind={industry} | EarnGwth={earnings_growth:.1%}"
                    progress_callback(f"🔎 {symbol}: {details} -> {status_text} ({score:.1f})", 0, 'detail')

                if score > 0:
                    candidates.append((symbol, score))
            
            except Exception as e:
                logger.debug(f"Error screening {symbol} for growth: {e}")
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
    
    def screen_value(self, top_n: int = 10, progress_callback=None) -> List[Tuple[str, float]]:
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
        metrics = config_manager.get_metrics().get('value', {})
        industry_avgs = self.calculate_industry_averages()
        
        for symbol, data in self.stock_data.items():
            try:
                score = 0
                
                # Quality filters
                if data.get('market_cap', 0) < 1_000_000_000:  # $1B minimum
                    continue
                if data.get('current_price', 0) < 5:
                    continue
                
                industry = data.get('industry', 'Unknown')
                ind_stats = industry_avgs.get(industry, {})
                avg_pe = ind_stats.get('avg_pe', 20)
                avg_peg = ind_stats.get('avg_peg', 2)
                avg_fcf = ind_stats.get('avg_fcf_share', 0)
                
                # Valuation metrics (Undervalued vs Peers)
                pe_ratio = data.get('pe_ratio', 999)
                peg_ratio = data.get('peg_ratio', 999)
                
                # Check 1: P/E < Industry Average
                if 0 < pe_ratio < avg_pe:
                    score += (avg_pe - pe_ratio) * 5
                
                # Check 2: PEG Ratio (Growth at a Reasonable Price)
                # Configurable max PEG (usually < 1 or < 2)
                if 0 < peg_ratio < metrics.get('max_peg_ratio', 2.0):
                    score += (2.0 - peg_ratio) * 20
                    
                # Check 3: Check for stocks undervalued financially compared to peers (Cashflow per share)
                fcf = data.get('free_cash_flow', 0)
                shares = data.get('shares_outstanding', 1)
                fcf_per_share = fcf / shares if shares > 0 else 0
                
                if fcf_per_share > avg_fcf:
                    score += 30 # Bonus for being a cash cow vs peers
                
                # Note: "In value, do not use the good dividends as a metric" -> REMOVED Dividend Logic.
                
                # Financial health validation
                debt_to_equity = data.get('debt_to_equity', 999)
                if debt_to_equity < 0.5:
                    score += 10
                
                # Report detailed finding
                if progress_callback:
                    status_text = "PASS" if score > 0 else "FAIL"
                    price = data.get('current_price', 0)
                    change = data.get('day_change_pct', 0) * 100
                    trend = "🟢" if change >= 0 else "🔴"
                    price_str = f"${price:.2f} {trend} {change:+.2f}%"
                    
                    details = f"{price_str} | P/E={pe_ratio:.1f} (Avg {avg_pe:.1f}) | PEG={peg_ratio:.2f}"
                    progress_callback(f"🔎 {symbol}: {details} -> {status_text} ({score:.1f})", 0, 'detail')

                if score > 0:
                    candidates.append((symbol, score))
            
            except Exception as e:
                logger.debug(f"Error screening {symbol} for value: {e}")
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
    
    def screen_speculative(self, top_n: int = 5, progress_callback=None) -> List[Tuple[str, float]]:
        """
        Speculative/DeGen strategy: Find low-priced stocks with extreme momentum and volume anomalies.
        These are "leap of faith" trades. We look for:
        - Price < $10
        - High short-term momentum (RSI > 60 or massive daily change)
        - Extreme volume spikes (Volume Ratio > 2.5)
        - **NEW: High Social Consensus from eToro Top Investors**
        """
        candidates = []
        
        # Get social consensus to artificially boost trending retail stocks
        social_consensus = etoro_scraper.get_trending_social_stocks(min_consensus_threshold=2)
        
        for symbol, data in self.stock_data.items():
            try:
                score = 0
                price = data.get('current_price', 0)
                
                # Filter OUT expensive, safe stocks. We WANT penny/small caps.
                if price == 0 or price > 15:
                    continue
                
                vol_ratio = data.get('volume_ratio', 1.0)
                rsi = data.get('rsi_14', 50)
                change = data.get('day_change_pct', 0) * 100
                
                # Check 1: Volume Anomaly (Most important for penny stocks)
                if vol_ratio > 3.0:
                    score += 50
                elif vol_ratio > 2.0:
                    score += 25
                elif vol_ratio < 1.0:
                    continue # Ignore low volume penny stocks, too dangerous/illiquid
                    
                # Check 2: Momentum / RSI
                if rsi > 70:
                    # Normally bad, but in a pump, this is what we want
                    score += 20
                elif rsi > 60:
                    score += 10
                    
                # Check 3: Daily Price Action
                if change > 5.0:
                    score += int(change) # Massive bumps for huge gains
                elif change < 0:
                    # Don't catch falling knives in penny stocks
                    continue
                    
                # Check 4: eToro Social Consensus (Meta-Copier Bonus)
                if symbol in social_consensus:
                    score += 50 # Massive boost for trending social stocks
                    if progress_callback:
                        progress_callback(f"🔥 ETORO CONSENSUS MATCH: {symbol} is trending among Top Investors!", 0, 'detail')
                    
                if progress_callback:
                    status_text = "PASS" if score > 0 else "FAIL"
                    trend = "🟢" if change >= 0 else "🔴"
                    price_str = f"${price:.2f} {trend} {change:+.2f}%"
                    
                    details = f"{price_str} | Vol={vol_ratio:.1f}x | RSI={rsi:.1f}"
                    progress_callback(f"🎰 {symbol}: {details} -> {status_text} ({score:.1f})", 0, 'detail')

                if score > 30: # Requires high conviction to pass
                    candidates.append((symbol, score))
            
            except Exception as e:
                logger.debug(f"Error screening {symbol} for speculative: {e}")
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
    
    def screen_crypto(self, progress_callback=None) -> Dict[str, List[Tuple[str, float]]]:
        """
        Screen crypto for multiple bots (Moonshot, Conservative, Custom).
        Returns dict: {'BotName': [(symbol, score), ...]}
        """
        results = {}
        
        # Get bot configs
        metrics_config = config_manager.get_metrics()
        bots = metrics_config.get('crypto_bots', [])
        
        # If still old config format, convert on fly or default
        if not bots and metrics_config.get('crypto'):
             # Fallback to old single bot if config update failed
             bots = [{'name': 'Legacy', 'strategy': metrics_config['crypto'].get('strategy'), 'symbols': metrics_config['crypto'].get('symbols')}]
        
        for bot in bots:
            if not bot.get('enabled', True):
                continue
                
            bot_name = bot['name']
            strategy = bot['strategy']
            universe = bot['symbols']
            
            # Dynamically inject trending cryptos if it's the DegenCrypto bot
            if bot_name == 'DegenCrypto':
                trending = crypto_discoverer.get_trending_symbols(format_suffix="/USD")
                for coin in trending:
                    if coin not in universe:
                        universe.append(coin)
            
            logger.info(f"🤖 Running {bot_name} Bot ({strategy}) on {len(universe)} symbols...")
            
            candidates = []
            
            # Fetch data for this bot's universe
            crypto_data = stock_data_provider.fetch_multiple(universe)
            
            for symbol, data in crypto_data.items():
                try:
                    score = 0
                    clean_symbol = symbol.replace("/USD", "")
                    
                    # --- MOONSHOT STRATEGY ---
                    if strategy == 'moonshot':
                        # High Risk, High Reward
                        price_change = data.get('price_change_5d', 0)
                        if price_change > 3: score += price_change * 10
                        if price_change < 0: continue
                        
                        volume_ratio = data.get('volume_ratio', 0)
                        if volume_ratio > 1.2: score += (volume_ratio - 1) * 30
                        
                        rsi = data.get('rsi', 50)
                        if 60 <= rsi <= 85: score += 20 + (rsi - 60)
                        elif rsi < 50: score -= 20
                        
                    # --- CONSERVATIVE STRATEGY ---
                    elif strategy == 'dip_buy':
                        # Buy Fear, Sell Greed
                        rsi = data.get('rsi', 50)
                        if rsi < 35: score += (35 - rsi) * 5 # Buy the dip
                        elif rsi > 60: score -= 50 # Avoid heat
                        
                        market_cap = data.get('market_cap', 0) # Prefer safety (not available for all, but conceptually)
                        score += 10 # Base score for blue chips
                        
                    # --- CUSTOM STRATEGY ---
                    elif strategy == 'custom':
                        # Simple Momentum or MA Crossover (Default)
                        price = data.get('current_price', 0)
                        ma50 = data.get('50day_avg', 0)
                        if price > ma50: score += 20
                        
                        rsi = data.get('rsi', 50)
                        if 40 <= rsi <= 70: score += 10
                        
                    # --- SPECULATIVE / DEGEN STRATEGY ---
                    elif strategy == 'speculative':
                        # Explicitly looking for penny cryptos with explosive momentum
                        price = data.get('current_price', 0)
                        if price > 5.0: # Ignore expensive coins
                            continue
                            
                        vol_ratio = data.get('volume_ratio', 1.0)
                        rsi = data.get('rsi', 50)
                        change = data.get('price_change_24h', 0) # Fallback to a common key, or day_change_pct
                        if 'day_change_pct' in data:
                            change = data['day_change_pct'] * 100
                            
                        # High volume is required
                        if vol_ratio > 3.0:
                            score += 50
                        elif vol_ratio > 2.0:
                            score += 25
                            
                        # High RSI = momentum breakout
                        if rsi > 70:
                            score += 20
                        elif rsi > 60:
                            score += 10
                            
                        if change > 5.0:
                            score += int(change)
                        elif change < 0:
                            continue # Don't buy dropping penny cryptos
                    
                    
                    # Logging
                    if progress_callback and score > 0:
                         progress_callback(f"🤖 {bot_name}: Analyzed {clean_symbol} -> Score {score:.1f}", 0, 'detail')

                    if score > 0:
                        candidates.append((symbol, score)) # Keep full symbol for execution
                        
                except Exception as e:
                    logger.debug(f"Error screening {symbol} for {bot_name}: {e}")
            
            candidates.sort(key=lambda x: x[1], reverse=True)
            results[bot_name] = candidates[:3] # Top 3 per bot
            
        return results

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
            # Shorten error message to avoid spamming HTML in logs if Yahoo fails
            error_str = str(e)
            if len(error_str) > 200:
                error_str = error_str[:200] + "..."
            logger.error(f"Error checking market sentiment: {error_str}")
            return "neutral"

    def run_all_strategies(self, skip_fetch=False, progress_callback=None) -> Dict[str, List[str]]:
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
            
        momentum_picks = self.screen_momentum(top_n=int(base_picks * self.strategy_weights['momentum']), progress_callback=progress_callback)
        growth_picks = self.screen_growth(top_n=int(base_picks * self.strategy_weights['growth']), progress_callback=progress_callback)
        value_picks = self.screen_value(top_n=int(base_picks * self.strategy_weights['value']), progress_callback=progress_callback)
        
        # Screen Speculative (Fixed small number of top picks)
        speculative_picks = self.screen_speculative(top_n=3, progress_callback=progress_callback)
        
        # Screen Crypto (Returns dict of lists)
        crypto_picks = self.screen_crypto(progress_callback=progress_callback)
        
        results = {
            'momentum': [x[0] for x in momentum_picks],
            'growth': [x[0] for x in growth_picks],
            'value': [x[0] for x in value_picks],
            'speculative': [x[0] for x in speculative_picks],
            'crypto': {bot: [x[0] for x in picks] for bot, picks in crypto_picks.items()},
            'timestamp': datetime.now().isoformat(),
            'weights': self.strategy_weights,
            'market_sentiment': sentiment
        }
        
        # Combine unique symbols (stocks only for 'all' list to avoid confusion in main loop)
        all_symbols = list(set(results['momentum'] + results['growth'] + results['value'] + results['speculative']))
        results['all'] = all_symbols
        
        logger.info(f"Momentum picks ({len(momentum_picks)}): {results['momentum']}")
        logger.info(f"Growth picks ({len(growth_picks)}): {results['growth']}")
        logger.info(f"Value picks ({len(value_picks)}): {results['value']}")
        logger.info(f"Speculative picks ({len(speculative_picks)}): {results['speculative']}")
        logger.info(f"Crypto picks ({len(crypto_picks)}): {results['crypto']}")
        
        self.save_screening_results(results)
        logger.info(f"Total unique stocks selected: {len(all_symbols)}")
        
        return results
    
    
    def save_screening_results(self, results: Dict):
        """Save screening results to DB cache"""
        from .data.db import db
        try:
            db.save_screening_cache(results)
            logger.info("Saved screening results to DB")
        except Exception as e:
            logger.error(f"Error saving screening results: {e}")
    
    def load_screening_results(self) -> Dict:
        """Load latest screening results from DB"""
        from .data.db import db
        try:
            return db.load_screening_cache()
        except Exception as e:
            logger.error(f"Error loading screening results: {e}")
            return {'all': []}

# Global instance
screener = StockScreener()
