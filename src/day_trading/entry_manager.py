"""
Entry Manager
Orchestrates the entry decision process:
1. Checks technical signals (EntrySignals)
2. Applies discretionary filters (DiscretionaryFilter)
3. Calculates position size (RiskManager)
4. Returns final entry decision
"""

from typing import Dict
from ..utils import logger
from .entry_signals import entry_signals
from .discretionary_filter import discretionary_filter
from ..risk_manager import risk_manager
from config import DAY_TRADING_CONFIG

class EntryManager:
    """Manages trade entry decisions"""
    
    def __init__(self):
        pass
        
    def evaluate_entry(self, symbol: str) -> Dict:
        """
        Evaluate if we should enter a trade for the given symbol.
        
        Returns:
            Dict with decision details:
            {
                'enter': bool,
                'symbol': str,
                'shares': int,
                'entry_price': float,
                'stop_loss': float,
                'target': float,
                'setup_type': str,
                'reason': str
            }
        """
        # 1. Check Discretionary Filters First (Fail Fast)
        if not discretionary_filter.check_time_of_day():
            return {'enter': False, 'reason': 'Lunch hour'}
            
        if not discretionary_filter.check_market_alignment(direction='long'):
            return {'enter': False, 'reason': 'Market misalignment'}
            
        # 2. Check Technical Signals
        # Priority 1: ORB (if enabled)
        if DAY_TRADING_CONFIG.get('day_trading_strategies', {}).get('orb', True):
            orb_signal = entry_signals.detect_orb_breakout(symbol)
            if orb_signal['signal']:
                return self._finalize_entry(symbol, orb_signal)
                
        # Priority 2: VWAP Pullback (if enabled)
        if DAY_TRADING_CONFIG.get('day_trading_strategies', {}).get('vwap_pullback', True):
            vwap_signal = entry_signals.detect_vwap_pullback(symbol)
            if vwap_signal['signal']:
                return self._finalize_entry(symbol, vwap_signal)
                
        return {'enter': False, 'reason': 'No valid signal'}
        
    def _finalize_entry(self, symbol: str, signal: Dict) -> Dict:
        """Calculate size and finalize entry"""
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        
        # Calculate Position Size based on Risk
        risk_pct = DAY_TRADING_CONFIG.get('per_trade_risk_pct', 1.0)
        shares = risk_manager.calculate_position_size_by_risk(
            entry_price=entry_price,
            stop_price=stop_loss,
            risk_pct=risk_pct
        )
        
        if shares <= 0:
            return {'enter': False, 'reason': 'Calculated 0 shares (risk too high?)'}
            
        logger.info(f"✅ ENTRY SIGNAL: {symbol} {signal['strategy']} | Shares: {shares} | Stop: {stop_loss}")
        
        return {
            'enter': True,
            'symbol': symbol,
            'shares': shares,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': signal['target'],
            'setup_type': signal['strategy'],
            'reason': f"{signal['strategy']} signal detected"
        }

# Global instance
entry_manager = EntryManager()
