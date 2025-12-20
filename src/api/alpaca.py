"""
Alpaca API Client Adapter
Acts as a drop-in replacement for the legacy Robinhood client.
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, AssetClass
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
from ..utils import logger

class AlpacaClient:
    """Alpaca API wrapper implementing the interface expected by the bot"""
    
    def __init__(self, api_key, secret_key, paper=True):
        self.trading_client = TradingClient(api_key, secret_key, paper=paper)
        self.stock_data_client = StockHistoricalDataClient(api_key, secret_key)
        self.crypto_data_client = CryptoHistoricalDataClient(api_key, secret_key)
        self.paper = paper
        logger.info(f"Alpaca client initialized ({'paper' if paper else 'live'} trading)")

    # =========================================================================
    # ACCOUNT & AUTHENTICATION
    # =========================================================================

    async def login_to_robinhood(self):
        """Mock login for compatibility"""
        # Alpaca uses API keys, so we just verify connection or return success
        try:
            self.trading_client.get_account()
            return {'expires_in': 86400} # Fake token expiry
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            return None

    def get_account_info(self):
        """Get account info mapped to expected format"""
        from alpaca.common.exceptions import APIError
        
        try:
            account = self.trading_client.get_account()
            return {
                'buying_power': float(account.buying_power),
                'portfolio_cash': float(account.cash),
                'portfolio_equity': float(account.equity),
                'portfolio_value': float(account.portfolio_value),
            }
        except APIError as e:
            logger.error(f"Alpaca API error getting account info: {e.status_code} - {e.message}")
            raise
        except (ValueError, AttributeError) as e:
            logger.error(f"Data parsing error in get_account_info: {e}")
            return {'buying_power': 0.0, 'portfolio_cash': 0.0, 'portfolio_equity': 0.0, 'portfolio_value': 0.0}
        except Exception as e:
            logger.error(f"Unexpected error getting account info: {type(e).__name__}: {e}")
            raise

    # =========================================================================
    # PORTFOLIO & POSITIONS
    # =========================================================================

    def get_portfolio_stocks(self):
        """Get stock positions in expected dict format"""
        try:
            positions = self.trading_client.get_all_positions()
            portfolio = {}
            for p in positions:
                if p.asset_class != AssetClass.CRYPTO:
                    portfolio[p.symbol] = {
                        'quantity': float(p.qty),
                        'price': float(p.current_price),
                        'average_buy_price': float(p.avg_entry_price),
                        'equity': float(p.market_value),
                        'type': 'stock',
                        'name': p.symbol # Fallback
                    }
            return portfolio
        except Exception as e:
            logger.error(f"Error getting portfolio stocks: {e}")
            return {}

    def get_crypto_positions(self):
        """Get crypto positions in expected list format"""
        try:
            positions = self.trading_client.get_all_positions()
            crypto_positions = []
            for p in positions:
                if p.asset_class == AssetClass.CRYPTO:
                    crypto_positions.append({
                        'symbol': p.symbol,
                        'quantity': float(p.qty),
                        'cost_basis': {'amount': float(p.cost_basis)},
                        'price': float(p.current_price),
                        'type': 'crypto'
                    })
            return crypto_positions
        except Exception as e:
            logger.error(f"Error getting crypto positions: {e}")
            return []

    def get_portfolio_overview(self):
        """Get combined portfolio overview"""
        return self.get_portfolio_stocks()

    # =========================================================================
    # MARKET DATA
    # =========================================================================

    def get_current_price(self, symbol):
        """Get current price for a stock"""
        # Note: Real-time data might require a paid subscription for some feeds.
        # Using snapshot or latest trade.
        try:
            # For simplicity using historical latest bar or snapshot if available
            # Alpaca-py doesn't have a simple 'get_price' for free tier easily without setting up streams.
            # We'll use get_latest_trade for stocks.
            from alpaca.data.requests import StockLatestTradeRequest
            req = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trade = self.stock_data_client.get_stock_latest_trade(req)
            return float(trade[symbol].price)
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return 0.0

    def get_crypto_quote(self, symbol):
        """Get crypto quote"""
        try:
            from alpaca.data.requests import CryptoLatestQuoteRequest
            # Alpaca crypto symbols are like 'BTC/USD' but positions might be 'BTCUSD'
            # Normalize symbol
            if '/' not in symbol and symbol.endswith('USD'):
                symbol = symbol[:-3] + '/USD'
                
            req = CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.crypto_data_client.get_crypto_latest_quote(req)
            return {'mark_price': float(quote[symbol].ask_price)} # Use ask or mid
        except Exception as e:
            logger.error(f"Error getting crypto quote for {symbol}: {e}")
            return {'mark_price': 0.0}

    def get_historical_data(self, symbol, interval="5minute", span="day"):
        """Get historical data as DataFrame"""
        try:
            end = datetime.now()
            start = end - timedelta(days=1)
            timeframe = TimeFrame.Minute
            
            if span == "year":
                start = end - timedelta(days=365)
                timeframe = TimeFrame.Day
            elif span == "day":
                start = end - timedelta(days=1) # Or business day
                timeframe = TimeFrame.Minute # 5 min approximation
            elif span.endswith("d"):
                try:
                    days = int(span[:-1])
                    start = end - timedelta(days=days)
                    # If looking back many days, day bars might be better, but if interval is specified, use that.
                    # Default to Minute if not specified or "5minute"
                    timeframe = TimeFrame.Minute
                except:
                    start = end - timedelta(days=1)
            elif span == "month" or span.endswith("mo"):
                 start = end - timedelta(days=30)
                 timeframe = TimeFrame.Minute

            
            # Map interval string to TimeFrame if needed, for now simplified
            
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=start,
                end=end
            )
            bars = self.stock_data_client.get_stock_bars(req)
            df = bars.df
            # Reset index to get 'timestamp' as column if needed, or keep as is.
            # The bot expects specific columns likely.
            # Robinhood usually returns list of dicts. We'll convert DF to that if needed, 
            # but the enrichment functions below expect DF or list.
            # Let's return DataFrame as it's easier for enrichment.
            return df
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return pd.DataFrame()

    def get_ratings(self, symbol):
        """Mock ratings data"""
        return {'summary': 'Neutral', 'score': 5}

    def get_watchlist_stocks(self, watchlist_name):
        """Get watchlist (Mock or Alpaca Watchlist)"""
        # For now, return empty or specific list based on name
        return []

    def is_market_open(self):
        """Check if market is open"""
        try:
            clock = self.trading_client.get_clock()
            return clock.is_open
        except Exception:
            return False

    # =========================================================================
    # TRADING
    # =========================================================================

    def buy_stock(self, symbol, quantity):
        try:
            req = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            order = self.trading_client.submit_order(req)
            return self._format_order_response(order)
        except Exception as e:
            logger.error(f"Buy stock error: {e}")
            return {'detail': str(e)}

    def sell_stock(self, symbol, quantity):
        try:
            # Check if we have position first to avoid shorting if not intended
            req = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            order = self.trading_client.submit_order(req)
            return self._format_order_response(order)
        except Exception as e:
            logger.error(f"Sell stock error: {e}")
            return {'detail': str(e)}

    def buy_crypto(self, symbol, amount_usd):
        try:
            req = MarketOrderRequest(
                symbol=symbol,
                notional=amount_usd,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            order = self.trading_client.submit_order(req)
            return self._format_order_response(order)
        except Exception as e:
            logger.error(f"Buy crypto error: {e}")
            return {'detail': str(e)}

    def sell_crypto(self, symbol, amount_usd):
        try:
            req = MarketOrderRequest(
                symbol=symbol,
                notional=amount_usd,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            order = self.trading_client.submit_order(req)
            return self._format_order_response(order)
        except Exception as e:
            logger.error(f"Sell crypto error: {e}")
            return {'detail': str(e)}

    def _format_order_response(self, order):
        """Format Alpaca order to look like Robinhood response for compatibility"""
        return {
            'id': str(order.id),
            'state': str(order.status),
            'price': float(order.filled_avg_price) if order.filled_avg_price else 0.0,
            'quantity': float(order.qty) if order.qty else 0.0,
            'detail': 'Order placed successfully'
        }
        
    def extract_buy_response_data(self, resp):
        return resp
        
    def extract_sell_response_data(self, resp):
        return resp

    def close_all_positions(self):
        """Close all open positions immediately"""
        try:
            # cancel_orders=True will cancel all open orders as well
            self.trading_client.close_all_positions(cancel_orders=True)
            return {'status': 'success', 'message': 'All positions closed and orders cancelled'}
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return {'status': 'error', 'message': str(e)}

    # =========================================================================
    # TECHNICAL ANALYSIS & ENRICHMENT
    # =========================================================================

    def enrich_with_rsi(self, stock_data, historical_data, symbol):
        """Calculate RSI"""
        try:
            if historical_data.empty:
                stock_data['rsi'] = 50
                return stock_data
            
            close = historical_data['close']
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            stock_data['rsi'] = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        except Exception as e:
            logger.error(f"RSI error for {symbol}: {e}")
            stock_data['rsi'] = 50
        return stock_data

    def enrich_with_vwap(self, stock_data, historical_data, symbol):
        """Calculate VWAP"""
        try:
            if historical_data.empty:
                stock_data['vwap'] = stock_data.get('price', 0)
                return stock_data
                
            v = historical_data['volume'].values
            tp = (historical_data['high'] + historical_data['low'] + historical_data['close']) / 3
            vwap = (tp * v).cumsum() / v.cumsum()
            stock_data['vwap'] = vwap.iloc[-1] if not pd.isna(vwap.iloc[-1]) else stock_data.get('price', 0)
        except Exception:
            stock_data['vwap'] = stock_data.get('price', 0)
        return stock_data

    def enrich_with_moving_averages(self, stock_data, historical_data, symbol):
        """Calculate MA"""
        try:
            if historical_data.empty:
                return stock_data
            
            close = historical_data['close']
            stock_data['sma_200'] = close.rolling(window=200).mean().iloc[-1]
            stock_data['sma_50'] = close.rolling(window=50).mean().iloc[-1]
        except Exception:
            pass
        return stock_data

    def enrich_with_analyst_ratings(self, stock_data, ratings_data):
        stock_data['analyst_rating'] = ratings_data.get('summary', 'Neutral')
        return stock_data

    def enrich_with_pdt_restrictions(self, stock_data, symbol):
        # Alpaca handles PDT checks on their end, but we can mock this
        stock_data['is_buy_pdt_restricted'] = False
        stock_data['is_sell_pdt_restricted'] = False
        return stock_data

# Singleton accessor
alpaca_client = None

def get_alpaca_client(api_key=None, secret_key=None, paper=True):
    global alpaca_client
    if alpaca_client is None:
        if not api_key or not secret_key:
            logger.error("Alpaca API credentials missing!")
            return None
        alpaca_client = AlpacaClient(api_key, secret_key, paper)
    return alpaca_client
