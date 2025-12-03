"""
Risk Management Module for Robinhood AI Trading Bot.
Handles Stop-Loss, Take-Profit, and Daily Loss Limits.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .utils import logger
from .api import robinhood

class RiskManager:
    def __init__(self, 
                 stop_loss_pct: float = 0.05, 
                 take_profit_pct: float = 0.10,
                 max_daily_loss_pct: float = 0.02):
        """
        Initialize Risk Manager.
        
        Args:
            stop_loss_pct: Percentage drop to trigger sell (e.g., 0.05 for 5%)
            take_profit_pct: Percentage gain to trigger sell (e.g., 0.10 for 10%)
            max_daily_loss_pct: Max daily portfolio loss before halting trading
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.daily_starting_balance = 0.0
        self.trading_halted = False
        self.last_check_time = datetime.now()
        
        # Track initial entry prices for positions if not available from API
        self.position_entry_prices = {}

    def set_starting_balance(self, balance: float):
        """Set the portfolio balance at the start of the day"""
        self.daily_starting_balance = balance
        self.trading_halted = False
        logger.info(f"Risk Manager initialized with starting balance: ${balance:.2f}")

    def check_portfolio_health(self, current_balance: float) -> bool:
        """
        Check if total portfolio loss exceeds daily limit.
        Returns True if healthy, False if trading should be halted.
        """
        if self.daily_starting_balance <= 0:
            return True
            
        loss_pct = (self.daily_starting_balance - current_balance) / self.daily_starting_balance
        
        if loss_pct >= self.max_daily_loss_pct:
            if not self.trading_halted:
                logger.critical(f"🚨 CIRCUIT BREAKER TRIGGERED! Daily loss {loss_pct:.2%} exceeds limit {self.max_daily_loss_pct:.2%}")
                self.trading_halted = True
            return False
            
        return True

    def check_position_risk(self, symbol: str, current_price: float, avg_buy_price: float, quantity: float) -> Optional[str]:
        """
        Check if a position has hit stop-loss or take-profit levels.
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
            avg_buy_price: Average purchase price
            quantity: Number of shares
            
        Returns:
            'sell_stop_loss' if stop loss triggered
            'sell_take_profit' if take profit triggered
            None if position is safe
        """
        if self.trading_halted:
            return None # Don't trigger individual sells if whole bot is halted (manual intervention needed)

        if avg_buy_price <= 0:
            return None

        # Calculate percentage change
        pct_change = (current_price - avg_buy_price) / avg_buy_price
        
        # Check Stop Loss
        if pct_change <= -self.stop_loss_pct:
            logger.warning(f"🛑 STOP-LOSS TRIGGERED for {symbol}: {pct_change:.2%} drop (Price: ${current_price}, Buy: ${avg_buy_price})")
            return 'sell_stop_loss'
            
        # Check Take Profit
        if pct_change >= self.take_profit_pct:
            logger.info(f"💰 TAKE-PROFIT TRIGGERED for {symbol}: {pct_change:.2%} gain (Price: ${current_price}, Buy: ${avg_buy_price})")
            return 'sell_take_profit'
            
        return None

    def monitor_positions(self, portfolio_stocks: Dict) -> List[Dict]:
        """
        Monitor all positions and return list of necessary actions.
        """
        actions = []
        
        for symbol, stock_data in portfolio_stocks.items():
            try:
                current_price = float(stock_data.get('price', 0))
                avg_buy_price = float(stock_data.get('average_buy_price', 0))
                quantity = float(stock_data.get('quantity', 0))
                
                if current_price > 0 and avg_buy_price > 0 and quantity > 0:
                    decision = self.check_position_risk(symbol, current_price, avg_buy_price, quantity)
                    
                    if decision:
                        actions.append({
                            'symbol': symbol,
                            'action': 'sell',
                            'reason': decision,
                            'quantity': quantity,
                            'price': current_price
                        })
            except Exception as e:
                logger.error(f"Error checking risk for {symbol}: {e}")
                
        return actions

# Global instance
risk_manager = RiskManager()
