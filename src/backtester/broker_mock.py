import pandas as pd
from datetime import datetime
from src.utils import logger

class MockBroker:
    def __init__(self, initial_cash=100000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.portfolio = {} # {symbol: {'quantity': 10, 'avg_price': 100}}
        self.orders = []
        self.current_time = None
        self.historical_data = {} # {symbol: DataFrame}
        
        # Performance Tracking
        self.equity_curve = []
        
    def set_data(self, data_dict):
        """Load historical data: {symbol: DataFrame(OHLCV)}"""
        self.historical_data = data_dict

    def update_time(self, timestamp):
        """Tick the clock"""
        self.current_time = timestamp
        self._record_equity()

    def get_current_price(self, symbol):
        """Get price at current simulation time"""
        if symbol not in self.historical_data:
            return None
        
        df = self.historical_data[symbol]
        # Find row closest to current_time (assuming sorted)
        # For simplicity, using exact match or ffill
        try:
            # This is slow for loop, optimized would be iterator
            # Assuming df index is datetime
            row = df.asof(self.current_time)
            return row['close'] if pd.notnull(row['close']) else None
        except Exception:
            return None

    # --- Broker Interface ---
    
    def get_account_info(self):
        equity = self.calculate_equity()
        return {
            'portfolio_equity': equity,
            'portfolio_cash': self.cash,
            'buying_power': self.cash # Simplified
        }

    def get_portfolio_stocks(self):
        # Format like Alpaca: {symbol: {qty, price, market_value, ...}}
        res = {}
        for sym, pos in self.portfolio.items():
            current_price = self.get_current_price(sym) or pos['avg_price']
            res[sym] = {
                'quantity': pos['quantity'],
                'average_buy_price': pos['avg_price'],
                'price': current_price,
                'market_value': pos['quantity'] * current_price
            }
        return res

    def get_crypto_positions(self):
        return [] # TODO: Support crypto

    def submit_order(self, symbol, quantity, side, type='market', time_in_force='day'):
        """Simulate order execution"""
        price = self.get_current_price(symbol)
        if not price:
            logger.warning(f"Backtest: No price for {symbol} at {self.current_time}")
            return None

        cost = price * quantity
        
        if side == 'buy':
            if self.cash >= cost:
                self.cash -= cost
                if symbol not in self.portfolio:
                    self.portfolio[symbol] = {'quantity': 0, 'avg_price': 0}
                
                # Update avg price
                old_qty = self.portfolio[symbol]['quantity']
                old_cost = old_qty * self.portfolio[symbol]['avg_price']
                new_qty = old_qty + quantity
                new_avg = (old_cost + cost) / new_qty
                
                self.portfolio[symbol]['quantity'] = new_qty
                self.portfolio[symbol]['avg_price'] = new_avg
                action = "BOUGHT"
            else:
                logger.warning(f"Backtest: Insufficient funds for {symbol}")
                return None
                
        elif side == 'sell':
            if symbol in self.portfolio and self.portfolio[symbol]['quantity'] >= quantity:
                self.cash += cost
                self.portfolio[symbol]['quantity'] -= quantity
                if self.portfolio[symbol]['quantity'] <= 0:
                    del self.portfolio[symbol]
                action = "SOLD"
            else:
                logger.warning(f"Backtest: Insufficient shares for {symbol}")
                return None

        # Record Order
        order = {
            'symbol': symbol,
            'side': side,
            'qty': quantity,
            'filled_avg_price': price,
            'status': 'filled',
            'created_at': self.current_time
        }
        self.orders.append(order)
        logger.info(f"BACKTEST {self.current_time}: {action} {quantity} {symbol} @ {price:.2f}")
        return order

    def calculate_equity(self):
        equity = self.cash
        for sym, pos in self.portfolio.items():
            price = self.get_current_price(sym)
            if price:
                equity += pos['quantity'] * price
        return equity

    def _record_equity(self):
        self.equity_curve.append({
            'timestamp': self.current_time,
            'equity': self.calculate_equity()
        })
