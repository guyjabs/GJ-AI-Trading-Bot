"""
Short Selling Strategy (IBKR Only)
Identifies bearish setups for short positions
"""

from typing import List, Dict
from datetime import datetime
from ..data.intraday_data import intraday_data
from ..research import news_agg
from ..utils import logger
from config import DAY_TRADING_CONFIG

class ShortStrategy:
    """Strategies for short selling (IBKR exclusive)"""
    
    def __init__(self):
        self.min_gap_pct = DAY_TRADING_CONFIG.get('min_gap_pct', 3.0)
        self.min_rvol = DAY_TRADING_CONFIG.get('min_rvol', 2.0)
        self.min_price = DAY_TRADING_CONFIG.get('min_price', 5.0)
        
    def scan_short_candidates(self, universe: List[str]) -> List[Dict]:
        """
        Find stocks to short:
        - Gapping DOWN >3%
        - Weak relative strength
        - Bearish news catalyst
        - Below VWAP
        - High volume (panic selling)
        """
        candidates = []
        
        logger.info("🔻 Scanning for SHORT candidates...")
        
        for symbol in universe:
            try:
                # Get gap percentage
                gap_pct = intraday_data.get_premarket_gap(symbol)
                
                # Look for GAP DOWN (negative gap)
                if gap_pct <= -self.min_gap_pct:
                    # Get RVOL
                    rvol = intraday_data.calculate_rvol(symbol)
                    
                    if rvol >= self.min_rvol:
                        # Check for bearish catalyst
                        catalyst = news_agg.get_catalyst_for_symbol(symbol)
                        
                        # Bearish catalysts: earnings miss, FDA rejection, regulatory issues
                        is_bearish = self._is_bearish_catalyst(catalyst)
                        
                        if is_bearish or abs(gap_pct) >= 5.0:  # Large gap = short even without catalyst
                            candidates.append({
                                'symbol': symbol,
                                'setup': 'gap_down_short',
                                'gap_pct': gap_pct,
                                'rvol': rvol,
                                'catalyst': catalyst.get('headline', 'Large gap'),
                                'score': abs(gap_pct) * rvol  # Higher score = better short
                            })
                            logger.info(f"🔻 SHORT CANDIDATE: {symbol} ({gap_pct:.2f}% gap, RVOL {rvol:.2f})")
                            
            except Exception as e:
                logger.debug(f"Error scanning {symbol} for shorts: {e}")
                
        # Sort by score (best shorts first)
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates
        
    def _is_bearish_catalyst(self, catalyst: Dict) -> bool:
        """Check if catalyst is bearish"""
        if not catalyst.get('has_catalyst'):
            return False
            
        catalyst_type = catalyst.get('catalyst_type', '')
        headline = catalyst.get('headline', '').lower()
        
        # Bearish keywords
        bearish_keywords = [
            'miss', 'misses', 'disappoints', 'falls', 'drops', 'plunges',
            'reject', 'rejected', 'denial', 'investigation', 'lawsuit',
            'downgrade', 'cuts', 'reduces', 'warning', 'concern'
        ]
        
        return any(keyword in headline for keyword in bearish_keywords)
        
    def detect_failed_breakout(self, symbol: str) -> Dict:
        """
        Failed breakout (bull trap) - SHORT SIGNAL
        
        Pattern:
        1. Stock breaks above resistance
        2. Immediately reverses (no follow-through)
        3. Falls back below breakout level
        
        Entry: Below breakout level
        Stop: Above recent high
        Target: 2:1 R:R
        """
        try:
            df = intraday_data.get_intraday_data(symbol, interval="5m", period="1d")
            if df.empty or len(df) < 20:
                return {'signal': False, 'reason': 'Insufficient data'}
                
            # Get recent high (last 10 bars)
            recent_high = df['High'].iloc[-10:].max()
            current_price = df['Close'].iloc[-1]
            
            # Check if we had a breakout attempt
            breakout_bars = df[df['High'] >= recent_high * 0.999].iloc[-5:]
            
            if len(breakout_bars) > 0:
                # Check if price is now BELOW the breakout level
                if current_price < recent_high * 0.995:
                    # Failed breakout confirmed
                    stop_loss = recent_high * 1.01  # Stop above recent high
                    risk = stop_loss - current_price
                    target = current_price - (risk * 2)  # 2:1 R:R
                    
                    return {
                        'signal': True,
                        'strategy': 'failed_breakout_short',
                        'direction': 'short',
                        'entry_price': current_price,
                        'stop_loss': stop_loss,
                        'target': target,
                        'setup_quality': 'high',
                        'timestamp': df.index[-1].isoformat()
                    }
                    
            return {'signal': False, 'reason': 'No failed breakout'}
            
        except Exception as e:
            logger.error(f"Error detecting failed breakout for {symbol}: {e}")
            return {'signal': False, 'reason': str(e)}
            
    def detect_vwap_rejection(self, symbol: str) -> Dict:
        """
        VWAP rejection - SHORT SIGNAL
        
        Pattern:
        1. Stock rallies to VWAP from below
        2. Gets rejected (can't break above)
        3. Starts to roll over
        
        Entry: Below VWAP with confirmation
        Stop: Above VWAP
        Target: 2:1 R:R
        """
        try:
            df = intraday_data.get_intraday_data(symbol, interval="1m", period="1d")
            if df.empty or len(df) < 30:
                return {'signal': False, 'reason': 'Insufficient data'}
                
            vwap = intraday_data.calculate_vwap(symbol)
            if not vwap:
                return {'signal': False, 'reason': 'No VWAP data'}
                
            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            
            # Check if price is below VWAP and falling
            if current_price < vwap and prev_price > current_price:
                # Check if we recently tested VWAP from below
                recent_bars = df.iloc[-10:]
                touched_vwap = any(abs(bar['High'] - vwap) / vwap < 0.002 for _, bar in recent_bars.iterrows())
                
                if touched_vwap:
                    # VWAP rejection confirmed
                    stop_loss = vwap * 1.005  # Stop slightly above VWAP
                    risk = stop_loss - current_price
                    target = current_price - (risk * 2)
                    
                    return {
                        'signal': True,
                        'strategy': 'vwap_rejection_short',
                        'direction': 'short',
                        'entry_price': current_price,
                        'stop_loss': stop_loss,
                        'target': target,
                        'setup_quality': 'medium',
                        'timestamp': df.index[-1].isoformat()
                    }
                    
            return {'signal': False, 'reason': 'No VWAP rejection'}
            
        except Exception as e:
            logger.error(f"Error detecting VWAP rejection for {symbol}: {e}")
            return {'signal': False, 'reason': str(e)}
            
    def detect_breakdown(self, symbol: str) -> Dict:
        """
        Breakdown below support - SHORT SIGNAL
        
        Pattern:
        1. Stock breaks below key support level
        2. Volume confirms the breakdown
        3. No immediate bounce
        
        Entry: Below support
        Stop: Above support
        Target: 2:1 R:R
        """
        try:
            df = intraday_data.get_intraday_data(symbol, interval="5m", period="1d")
            if df.empty or len(df) < 20:
                return {'signal': False, 'reason': 'Insufficient data'}
                
            # Identify support (recent lows)
            support = df['Low'].iloc[-20:-5].min()
            current_price = df['Close'].iloc[-1]
            current_volume = df['Volume'].iloc[-1]
            avg_volume = df['Volume'].iloc[-20:].mean()
            
            # Check if we broke below support with volume
            if current_price < support * 0.995 and current_volume > avg_volume * 1.5:
                stop_loss = support * 1.01
                risk = stop_loss - current_price
                target = current_price - (risk * 2)
                
                return {
                    'signal': True,
                    'strategy': 'breakdown_short',
                    'direction': 'short',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'setup_quality': 'high',
                    'timestamp': df.index[-1].isoformat()
                }
                
            return {'signal': False, 'reason': 'No breakdown'}
            
        except Exception as e:
            logger.error(f"Error detecting breakdown for {symbol}: {e}")
            return {'signal': False, 'reason': str(e)}

# Global instance
short_strategy = ShortStrategy()
