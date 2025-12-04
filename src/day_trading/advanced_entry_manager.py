"""
Advanced Entry Manager (IBKR)
Integrates long and short strategies with bracket orders
"""

from typing import Dict
from .entry_manager import entry_manager
from .short_strategy import short_strategy
from .bracket_manager import bracket_manager
from .discretionary_filter import discretionary_filter
from ..risk_manager import risk_manager
from ..utils import logger
from config import DAY_TRADING_CONFIG, IBKR_ADVANCED_FEATURES

class AdvancedEntryManager:
    """Advanced entry manager with long/short support (IBKR only)"""
    
    def __init__(self):
        self.enable_shorts = IBKR_ADVANCED_FEATURES.get('enable_short_selling', True)
        self.enable_brackets = IBKR_ADVANCED_FEATURES.get('enable_bracket_orders', True)
        
    def evaluate_entry(self, symbol: str, allow_short: bool = True) -> Dict:
        """
        Evaluate entry for both long and short opportunities.
        
        Args:
            symbol: Stock ticker
            allow_short: Whether to consider short positions
            
        Returns:
            Entry decision with side (long/short)
        """
        # 1. Check discretionary filters
        if not discretionary_filter.check_time_of_day():
            return {'enter': False, 'reason': 'Lunch hour'}
            
        # 2. Try LONG signals first
        long_decision = entry_manager.evaluate_entry(symbol)
        
        if long_decision['enter']:
            # Add bracket order info if enabled
            if self.enable_brackets:
                long_decision['use_bracket'] = True
            return long_decision
            
        # 3. Try SHORT signals (if enabled and allowed)
        if self.enable_shorts and allow_short:
            short_decision = self._evaluate_short_entry(symbol)
            
            if short_decision['enter']:
                if self.enable_brackets:
                    short_decision['use_bracket'] = True
                return short_decision
                
        return {'enter': False, 'reason': 'No valid long or short signal'}
        
    def _evaluate_short_entry(self, symbol: str) -> Dict:
        """Evaluate short entry signals"""
        # Check market alignment (for shorts, we want bearish market)
        if not discretionary_filter.check_market_alignment(direction='short'):
            return {'enter': False, 'reason': 'Market not aligned for shorts'}
            
        # Try different short patterns
        
        # 1. Failed Breakout
        failed_breakout = short_strategy.detect_failed_breakout(symbol)
        if failed_breakout['signal']:
            return self._finalize_short_entry(symbol, failed_breakout)
            
        # 2. VWAP Rejection
        vwap_rejection = short_strategy.detect_vwap_rejection(symbol)
        if vwap_rejection['signal']:
            return self._finalize_short_entry(symbol, vwap_rejection)
            
        # 3. Breakdown
        breakdown = short_strategy.detect_breakdown(symbol)
        if breakdown['signal']:
            return self._finalize_short_entry(symbol, breakdown)
            
        return {'enter': False, 'reason': 'No short signal'}
        
    def _finalize_short_entry(self, symbol: str, signal: Dict) -> Dict:
        """Finalize short entry with position sizing"""
        # Calculate position size based on risk
        shares = risk_manager.calculate_position_size_by_risk(
            entry_price=signal['entry_price'],
            stop_price=signal['stop_loss'],
            risk_pct=DAY_TRADING_CONFIG.get('per_trade_risk_pct', 1.0)
        )
        
        if shares == 0:
            return {'enter': False, 'reason': 'Position size too small'}
            
        logger.info(f"🔻 SHORT SIGNAL: {symbol} {signal['strategy']} | Shares: {shares} | Stop: {signal['stop_loss']}")
        
        return {
            'enter': True,
            'side': 'short',
            'symbol': symbol,
            'shares': shares,
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'target': signal['target'],
            'setup_type': signal['strategy'],
            'direction': 'short'
        }
        
    def execute_entry_with_bracket(self, decision: Dict) -> Dict:
        """
        Execute entry with bracket order (IBKR only).
        
        Args:
            decision: Entry decision from evaluate_entry
            
        Returns:
            Execution result
        """
        if not decision.get('enter'):
            return {'success': False, 'reason': 'No entry signal'}
            
        symbol = decision['symbol']
        side = 'SELL' if decision.get('side') == 'short' else 'BUY'
        
        # Create bracket
        if decision.get('use_bracket') and self.enable_brackets:
            result = bracket_manager.place_bracket_with_ibkr(
                symbol=symbol,
                side=side,
                entry_price=decision['entry_price'],
                stop_loss=decision['stop_loss'],
                target=decision['target'],
                shares=decision['shares']
            )
            
            if result['success']:
                logger.info(f"✅ Bracket order executed for {symbol}")
                return result
            else:
                logger.error(f"❌ Bracket order failed for {symbol}: {result.get('reason')}")
                return result
        else:
            # Regular entry without bracket
            logger.info(f"Executing regular {side} order for {symbol}")
            return {'success': False, 'reason': 'Bracket orders disabled or not requested'}

# Global instance
advanced_entry_manager = AdvancedEntryManager()
