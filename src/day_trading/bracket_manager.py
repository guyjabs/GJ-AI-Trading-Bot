"""
Bracket Order Manager (IBKR Only)
Manages bracket orders with auto stop-loss and take-profit
"""

from typing import Dict, Optional
from ..utils import logger
from config import DAY_TRADING_CONFIG

class BracketManager:
    """Manages bracket orders (IBKR exclusive)"""
    
    def __init__(self):
        self.min_rr = DAY_TRADING_CONFIG.get('min_reward_risk_ratio', 2.0)
        self.active_brackets = {}  # {symbol: bracket_info}
        
    def create_bracket(self, symbol: str, side: str, entry_price: float, 
                      stop_loss: float, target: float, shares: int) -> Dict:
        """
        Create bracket order with entry, stop, and target.
        
        Args:
            symbol: Stock ticker
            side: 'BUY' (long) or 'SELL' (short)
            entry_price: Entry limit price
            stop_loss: Stop loss price
            target: Take profit price
            shares: Number of shares
            
        Returns:
            Bracket order details
        """
        try:
            # Validate R:R ratio
            if side == 'BUY':
                risk = entry_price - stop_loss
                reward = target - entry_price
            else:  # SELL (short)
                risk = stop_loss - entry_price
                reward = entry_price - target
                
            if risk <= 0:
                logger.error(f"Invalid risk for {symbol}: {risk}")
                return {'success': False, 'reason': 'Invalid risk'}
                
            rr_ratio = reward / risk
            
            if rr_ratio < self.min_rr:
                logger.warning(f"R:R ratio {rr_ratio:.2f} below minimum {self.min_rr} for {symbol}")
                # Allow it but warn
                
            # Create bracket
            bracket = {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'shares': shares,
                'risk': risk,
                'reward': reward,
                'rr_ratio': rr_ratio,
                'status': 'pending'
            }
            
            self.active_brackets[symbol] = bracket
            
            logger.info(f"🎯 BRACKET CREATED: {symbol} {side} x{shares} | Entry: ${entry_price:.2f} | Stop: ${stop_loss:.2f} | Target: ${target:.2f} | R:R: {rr_ratio:.2f}")
            
            return {
                'success': True,
                'bracket': bracket
            }
            
        except Exception as e:
            logger.error(f"Error creating bracket for {symbol}: {e}")
            return {'success': False, 'reason': str(e)}
            
    def place_bracket_with_ibkr(self, symbol: str, side: str, entry_price: float,
                                stop_loss: float, target: float, shares: int):
        """
        Place bracket order via IBKR API.
        
        This creates 3 linked orders:
        1. Parent: Entry order (limit)
        2. Child 1: Stop loss (stop)
        3. Child 2: Take profit (limit)
        """
        try:
            from ..api.ibkr import get_ibkr_client
            
            ibkr = get_ibkr_client()
            
            if not ibkr.is_connected():
                logger.error("IBKR not connected. Cannot place bracket order.")
                return {'success': False, 'reason': 'Not connected to IBKR'}
                
            # Place bracket order
            trades = ibkr.place_bracket_order(
                symbol=symbol,
                side=side,
                quantity=shares,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=target
            )
            
            if trades:
                # Update bracket status
                if symbol in self.active_brackets:
                    self.active_brackets[symbol]['status'] = 'active'
                    self.active_brackets[symbol]['trades'] = trades
                    
                logger.info(f"✅ Bracket order placed for {symbol}")
                return {'success': True, 'trades': trades}
            else:
                logger.error(f"Failed to place bracket order for {symbol}")
                return {'success': False, 'reason': 'Order placement failed'}
                
        except Exception as e:
            logger.error(f"Error placing bracket order for {symbol}: {e}")
            return {'success': False, 'reason': str(e)}
            
    def get_bracket(self, symbol: str) -> Optional[Dict]:
        """Get active bracket for symbol"""
        return self.active_brackets.get(symbol)
        
    def remove_bracket(self, symbol: str):
        """Remove bracket (after exit)"""
        if symbol in self.active_brackets:
            del self.active_brackets[symbol]
            logger.info(f"Removed bracket for {symbol}")
            
    def calculate_optimal_target(self, entry_price: float, stop_loss: float, 
                                min_rr: float = None) -> float:
        """
        Calculate optimal profit target based on R:R ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            min_rr: Minimum reward:risk ratio (default from config)
            
        Returns:
            Target price
        """
        if min_rr is None:
            min_rr = self.min_rr
            
        risk = abs(entry_price - stop_loss)
        reward = risk * min_rr
        
        # Determine direction
        if entry_price > stop_loss:
            # Long position
            target = entry_price + reward
        else:
            # Short position
            target = entry_price - reward
            
        return target
        
    def get_active_brackets(self) -> Dict:
        """Get all active brackets"""
        return self.active_brackets.copy()

# Global instance
bracket_manager = BracketManager()
