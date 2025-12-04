"""
Interactive Brokers (IBKR) API Client
Provides advanced trading features not available in Robinhood:
- Short selling
- Bracket orders (auto stop/target)
- Level 2 market data
- Extended hours trading
"""

from ib_insync import *
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from ..utils import logger

class IBKRClient:
    """Interactive Brokers API wrapper"""
    
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        """
        Initialize IBKR client.
        
        Args:
            host: TWS/Gateway host (default: localhost)
            port: 7497 for paper trading, 7496 for live
            client_id: Unique client identifier
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        
    def connect(self):
        """Connect to TWS or IB Gateway"""
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            logger.info(f"✅ Connected to IBKR (Port: {self.port})")
            return True
        except Exception as e:
            logger.error(f"❌ IBKR connection failed: {e}")
            self.connected = False
            return False
            
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")
            
    def is_connected(self) -> bool:
        """Check if connected to IBKR"""
        return self.connected and self.ib.isConnected()
        
    # ==========================================
    # LONG POSITIONS (Standard)
    # ==========================================
    
    def buy_stock(self, symbol: str, quantity: int, order_type='MKT', limit_price: float = None):
        """
        Buy stock (go long).
        
        Args:
            symbol: Stock ticker
            quantity: Number of shares
            order_type: 'MKT' or 'LMT'
            limit_price: Required if order_type='LMT'
        """
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            if order_type == 'MKT':
                order = MarketOrder('BUY', quantity)
            else:
                order = LimitOrder('BUY', quantity, limit_price)
                
            trade = self.ib.placeOrder(contract, order)
            logger.info(f"📈 IBKR BUY: {symbol} x{quantity} @ {order_type}")
            return trade
        except Exception as e:
            logger.error(f"Error buying {symbol}: {e}")
            return None
            
    def sell_stock(self, symbol: str, quantity: int, order_type='MKT', limit_price: float = None):
        """
        Sell stock (close long position).
        
        Args:
            symbol: Stock ticker
            quantity: Number of shares
            order_type: 'MKT' or 'LMT'
            limit_price: Required if order_type='LMT'
        """
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            if order_type == 'MKT':
                order = MarketOrder('SELL', quantity)
            else:
                order = LimitOrder('SELL', quantity, limit_price)
                
            trade = self.ib.placeOrder(contract, order)
            logger.info(f"📉 IBKR SELL: {symbol} x{quantity} @ {order_type}")
            return trade
        except Exception as e:
            logger.error(f"Error selling {symbol}: {e}")
            return None
    
    # ==========================================
    # SHORT SELLING (IBKR Exclusive)
    # ==========================================
    
    def short_stock(self, symbol: str, quantity: int, order_type='MKT', limit_price: float = None):
        """
        Short sell a stock (IBKR only).
        
        Args:
            symbol: Stock ticker
            quantity: Number of shares to short
            order_type: 'MKT' or 'LMT'
            limit_price: Required if order_type='LMT'
        """
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            if order_type == 'MKT':
                order = MarketOrder('SELL', quantity)  # SELL = short
            else:
                order = LimitOrder('SELL', quantity, limit_price)
                
            trade = self.ib.placeOrder(contract, order)
            logger.info(f"🔻 IBKR SHORT: {symbol} x{quantity} @ {order_type}")
            return trade
        except Exception as e:
            logger.error(f"Error shorting {symbol}: {e}")
            return None
            
    def cover_short(self, symbol: str, quantity: int, order_type='MKT', limit_price: float = None):
        """
        Cover a short position (buy to close).
        
        Args:
            symbol: Stock ticker
            quantity: Number of shares to cover
            order_type: 'MKT' or 'LMT'
            limit_price: Required if order_type='LMT'
        """
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            if order_type == 'MKT':
                order = MarketOrder('BUY', quantity)  # BUY = cover short
            else:
                order = LimitOrder('BUY', quantity, limit_price)
                
            trade = self.ib.placeOrder(contract, order)
            logger.info(f"🔼 IBKR COVER: {symbol} x{quantity} @ {order_type}")
            return trade
        except Exception as e:
            logger.error(f"Error covering {symbol}: {e}")
            return None
    
    # ==========================================
    # BRACKET ORDERS (IBKR Exclusive)
    # ==========================================
    
    def place_bracket_order(self, symbol: str, side: str, quantity: int,
                           entry_price: float, stop_loss: float, take_profit: float):
        """
        Place bracket order with auto stop/target (IBKR only).
        
        Args:
            symbol: Stock ticker
            side: 'BUY' (long) or 'SELL' (short)
            quantity: Number of shares
            entry_price: Entry limit price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            List of 3 orders: [parent, stop, profit]
        """
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Create bracket using ib_insync helper
            bracket = self.ib.bracketOrder(
                action=side,
                quantity=quantity,
                limitPrice=entry_price,
                takeProfitPrice=take_profit,
                stopLossPrice=stop_loss
            )
            
            # Place all 3 orders together
            trades = []
            for order in bracket:
                trade = self.ib.placeOrder(contract, order)
                trades.append(trade)
                
            logger.info(f"🎯 IBKR BRACKET: {symbol} {side} x{quantity} | Entry: ${entry_price} | Stop: ${stop_loss} | Target: ${take_profit}")
            return trades
            
        except Exception as e:
            logger.error(f"Error placing bracket order for {symbol}: {e}")
            return None
    
    # ==========================================
    # LEVEL 2 DATA (IBKR Exclusive)
    # ==========================================
    
    def get_market_depth(self, symbol: str, num_rows: int = 10):
        """
        Get Level 2 market depth (order book).
        
        Args:
            symbol: Stock ticker
            num_rows: Number of price levels to retrieve
            
        Returns:
            Dict with bid/ask ladder
        """
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.reqMktDepth(contract, numRows=num_rows)
            
            # Wait for data
            self.ib.sleep(0.5)
            
            # Get ticker with depth
            ticker = self.ib.ticker(contract)
            
            return {
                'symbol': symbol,
                'bids': [(bid.price, bid.size) for bid in ticker.domBids],
                'asks': [(ask.price, ask.size) for ask in ticker.domAsks],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting market depth for {symbol}: {e}")
            return None
    
    # ==========================================
    # PORTFOLIO & ACCOUNT
    # ==========================================
    
    def get_portfolio(self) -> Dict:
        """
        Get current positions.
        
        Returns:
            Dict of positions by symbol
        """
        try:
            positions = self.ib.positions()
            portfolio = {}
            
            for pos in positions:
                symbol = pos.contract.symbol
                portfolio[symbol] = {
                    'symbol': symbol,
                    'quantity': pos.position,
                    'side': 'long' if pos.position > 0 else 'short',
                    'average_cost': pos.avgCost,
                    'market_value': pos.marketValue,
                    'unrealized_pnl': pos.unrealizedPNL,
                    'realized_pnl': pos.realizedPNL
                }
                
            return portfolio
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return {}
            
    def get_account_info(self) -> Dict:
        """
        Get account balance and buying power.
        
        Returns:
            Dict with account details
        """
        try:
            account_values = self.ib.accountValues()
            
            info = {}
            for val in account_values:
                if val.tag == 'NetLiquidation':
                    info['net_liquidation'] = float(val.value)
                elif val.tag == 'TotalCashValue':
                    info['cash'] = float(val.value)
                elif val.tag == 'BuyingPower':
                    info['buying_power'] = float(val.value)
                elif val.tag == 'GrossPositionValue':
                    info['gross_position_value'] = float(val.value)
                    
            return info
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
            
    def get_open_orders(self) -> List:
        """Get all open orders"""
        try:
            return self.ib.openOrders()
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
            
    def cancel_order(self, order):
        """Cancel an order"""
        try:
            self.ib.cancelOrder(order)
            logger.info(f"Cancelled order: {order.orderId}")
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")

# Global instance (initialized on demand)
ibkr_client = None

def get_ibkr_client(host='127.0.0.1', port=7497, client_id=1):
    """Get or create IBKR client singleton"""
    global ibkr_client
    if ibkr_client is None:
        ibkr_client = IBKRClient(host, port, client_id)
    return ibkr_client
