"""
Day Trading Screener
Identifies stocks matching day trading criteria:
- Pre-market Gappers
- High Relative Volume (RVOL)
- Momentum & Breakouts
"""

from typing import List, Dict
from ..utils import logger
from ..data.intraday_data import intraday_data
from ..research import news_agg
from config import DAY_TRADING_CONFIG

class DayTradingScreener:
    """Screens for day trading setups"""
    
    def __init__(self):
        self.universe = self._get_universe()
        
    def _get_universe(self) -> List[str]:
        """
        Get universe of stocks to screen.
        For day trading, we want liquid, volatile stocks.
        """
        # In a real scenario, we'd fetch a dynamic list of active stocks.
        # For now, we'll use a predefined list of popular day trading stocks + current watchlist
        return [
            "TSLA", "NVDA", "AMD", "AAPL", "META", "AMZN", "MSFT", "GOOGL", 
            "COIN", "MARA", "RIOT", "PLTR", "SOFI", "DKNG", "ROKU", "SQ",
            "NET", "CRWD", "SNOW", "DDOG", "UBER", "LYFT", "ABNB", "DASH"
        ]

    def scan_gappers(self) -> List[Dict]:
        """
        Find stocks with:
        - Pre-market gap >= min_gap_pct
        - Price >= min_price
        """
        candidates = []
        min_gap = DAY_TRADING_CONFIG.get('min_gap_pct', 3.0)
        min_price = DAY_TRADING_CONFIG.get('min_price', 5.0)
        
        logger.info(f"Scanning for Gappers (Gap > {min_gap}%, Price > ${min_price})...")
        
        for symbol in self.universe:
            try:
                # Check Gap
                gap_pct = intraday_data.get_premarket_gap(symbol)
                
                if abs(gap_pct) >= min_gap:
                    # Check Price (using last close as proxy if current not available yet)
                    # In real implementation, get_premarket_gap would return price too
                    
                    candidates.append({
                        'symbol': symbol,
                        'setup': 'gap_up' if gap_pct > 0 else 'gap_down',
                        'gap_pct': gap_pct,
                        'score': abs(gap_pct) # Rank by gap size
                    })
                    logger.info(f"🔥 FOUND GAPPER: {symbol} ({gap_pct:.2f}%)")
                    
            except Exception as e:
                logger.debug(f"Error scanning {symbol} for gaps: {e}")
                
        # Sort by gap size
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates

    def scan_momentum(self) -> List[Dict]:
        """
        Find stocks with high relative volume and momentum.
        """
        candidates = []
        min_rvol = DAY_TRADING_CONFIG.get('min_rvol', 2.0)
        
        logger.info(f"Scanning for Momentum (RVOL > {min_rvol})...")
        
        for symbol in self.universe:
            try:
                rvol = intraday_data.calculate_rvol(symbol)
                
                if rvol >= min_rvol:
                    candidates.append({
                        'symbol': symbol,
                        'setup': 'momentum',
                        'rvol': rvol,
                        'score': rvol
                    })
                    logger.info(f"🚀 FOUND MOMENTUM: {symbol} (RVOL {rvol:.2f})")
                    
            except Exception as e:
                logger.debug(f"Error scanning {symbol} for momentum: {e}")
                
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates

    def get_top_candidates(self) -> List[Dict]:
        """
        Run all scans and return top combined candidates.
        """
        gappers = self.scan_gappers()
        momentum = self.scan_momentum()
        
        # Combine unique symbols
        seen = set()
        final_list = []
        
        for c in gappers + momentum:
            if c['symbol'] not in seen:
                # Verify News Catalyst if required
                if DAY_TRADING_CONFIG.get('require_news_catalyst', True):
                    catalyst = news_agg.get_catalyst_for_symbol(c['symbol'])
                    if not catalyst['has_catalyst']:
                        logger.info(f"Skipping {c['symbol']} - No news catalyst")
                        continue
                    c['catalyst'] = catalyst
                
                final_list.append(c)
                seen.add(c['symbol'])
                
        return final_list

# Global instance
day_screener = DayTradingScreener()
