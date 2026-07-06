"""
eToro Execution Broker (Stub)

This class implements the Broker interface for eToro to prepare for 
the Popular Investor program.
Because eToro does not offer a standard retail API, this is currently 
designed to use a web-automation wrapper (e.g., fast-etoro or selenium) 
or to simply log paper trades.
"""

from typing import Dict, List
from ..utils import logger

class EtoroBroker:
    def __init__(self, is_paper: bool = True):
        self.is_paper = is_paper
        logger.info("🟢 Initializing eToro Broker (Popular Investor Mode)")
        if self.is_paper:
            logger.warning("eToro Broker running in PAPER mode. No real trades will be placed.")
            
    def get_account_info(self) -> Dict:
        """
        Mock account info for now.
        """
        return {
            'buying_power': 10000.00,
            'cash': 10000.00,
            'portfolio_value': 10000.00
        }
        
    def get_positions(self) -> List[Dict]:
        """
        Mock empty positions.
        """
        return []
        
    def submit_order(self, symbol: str, qty: float, side: str, order_type: str = 'market', limit_price: float = None) -> Dict:
        """
        Submit a trade to eToro.
        For now, just logs the action.
        """
        logger.info(f"🌐 ETORO EXECUTION: {side.upper()} {qty} shares of {symbol} (Type: {order_type})")
        return {
            'status': 'submitted',
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'platform': 'eToro'
        }
        
    def get_open_orders(self) -> List[Dict]:
        return []
        
    def cancel_order(self, order_id: str) -> bool:
        logger.info(f"🌐 ETORO EXECUTION: Cancelled order {order_id}")
        return True
