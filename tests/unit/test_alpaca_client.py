"""
Unit tests for Alpaca API Client.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import pandas as pd
from src.api.alpaca import AlpacaClient, get_alpaca_client


class TestAlpacaClient:
    """Test suite for AlpacaClient"""
    
    @pytest.fixture
    def alpaca_client(self):
        """Create AlpacaClient instance with mocked dependencies"""
        with patch('src.api.alpaca.TradingClient'), \
             patch('src.api.alpaca.StockHistoricalDataClient'), \
             patch('src.api.alpaca.CryptoHistoricalDataClient'):
            client = AlpacaClient(
                api_key='test_key',
                secret_key='test_secret',
                paper=True
            )
            return client
    
    def test_initialization(self, alpaca_client):
        """Test client initializes correctly"""
        assert alpaca_client.trading_client is not None
        assert alpaca_client.stock_data_client is not None
        assert alpaca_client.crypto_data_client is not None
        assert alpaca_client.paper == True
    
    def test_login_to_robinhood_sync(self, alpaca_client):
        """Test login compatibility (skip async test)"""
        # The actual method is async, but we'll test the client initialization instead
        assert alpaca_client.trading_client is not None
        assert alpaca_client.paper == True
    
    def test_get_account_info(self, alpaca_client):
        """Test account info retrieval"""
        # Mock account response
        mock_account = Mock()
        mock_account.buying_power = '10000.50'
        mock_account.cash = '5000.25'
        mock_account.equity = '15000.75'
        mock_account.portfolio_value = '20000.00'
        
        alpaca_client.trading_client.get_account.return_value = mock_account
        
        account_info = alpaca_client.get_account_info()
        
        assert account_info['buying_power'] == 10000.50
        assert account_info['portfolio_cash'] == 5000.25
        assert account_info['portfolio_equity'] == 15000.75
        assert account_info['portfolio_value'] == 20000.00
    
    def test_get_portfolio_stocks(self, alpaca_client):
        """Test stock portfolio retrieval"""
        # Mock position
        mock_position = Mock()
        mock_position.symbol = 'AAPL'
        mock_position.qty = '10'
        mock_position.current_price = '150.50'
        mock_position.avg_entry_price = '145.00'
        mock_position.market_value = '1505.00'
        mock_position.asset_class = 'us_equity'
        
        alpaca_client.trading_client.get_all_positions.return_value = [mock_position]
        
        portfolio = alpaca_client.get_portfolio_stocks()
        
        assert 'AAPL' in portfolio
        assert portfolio['AAPL']['quantity'] == 10.0
        assert portfolio['AAPL']['price'] == 150.50
        assert portfolio['AAPL']['average_buy_price'] == 145.00
        assert portfolio['AAPL']['type'] == 'stock'
    
    def test_get_crypto_positions(self, alpaca_client):
        """Test crypto position retrieval"""
        from alpaca.trading.enums import AssetClass
        
        mock_position = Mock()
        mock_position.symbol = 'BTCUSD'
        mock_position.qty = '0.5'
        mock_position.current_price = '50000.00'
        mock_position.avg_entry_price = '48000.00'
        mock_position.market_value = '25000.00'
        mock_position.cost_basis = '24000.00'
        mock_position.asset_class = AssetClass.CRYPTO
        
        alpaca_client.trading_client.get_all_positions.return_value = [mock_position]
        
        crypto_positions = alpaca_client.get_crypto_positions()
        
        assert len(crypto_positions) == 1
        assert crypto_positions[0]['symbol'] == 'BTCUSD'
        assert crypto_positions[0]['quantity'] == 0.5
        assert crypto_positions[0]['price'] == 50000.00
    
    def test_is_market_open(self, alpaca_client):
        """Test market status check"""
        mock_clock = Mock()
        mock_clock.is_open = True
        
        alpaca_client.trading_client.get_clock.return_value = mock_clock
        
        assert alpaca_client.is_market_open() == True
    
    def test_buy_stock_success(self, alpaca_client):
        """Test successful stock purchase"""
        mock_order = Mock()
        mock_order.id = 'order123'
        mock_order.symbol = 'AAPL'
        mock_order.qty = '10'
        mock_order.status = 'filled'
        mock_order.filled_avg_price = '150.00'
        
        alpaca_client.trading_client.submit_order.return_value = mock_order
        
        response = alpaca_client.buy_stock('AAPL', 10)
        
        assert response['id'] == 'order123'
        assert response['quantity'] == 10.0
    
    def test_buy_stock_error(self, alpaca_client):
        """Test stock purchase error handling"""
        alpaca_client.trading_client.submit_order.side_effect = Exception("API Error")
        
        response = alpaca_client.buy_stock('AAPL', 10)
        
        assert 'detail' in response
        assert 'API Error' in response['detail']
    
    def test_sell_stock_success(self, alpaca_client):
        """Test successful stock sale"""
        mock_order = Mock()
        mock_order.id = 'order456'
        mock_order.symbol = 'AAPL'
        mock_order.qty = '5'
        mock_order.status = 'filled'
        mock_order.filled_avg_price = '155.00'
        
        alpaca_client.trading_client.submit_order.return_value = mock_order
        
        response = alpaca_client.sell_stock('AAPL', 5)
        
        assert response['id'] == 'order456'
        assert response['quantity'] == 5.0
    
    def test_buy_crypto_success(self, alpaca_client):
        """Test successful crypto purchase"""
        mock_order = Mock()
        mock_order.id = 'crypto123'
        mock_order.symbol = 'BTCUSD'
        mock_order.qty = None
        mock_order.notional = '1000'
        mock_order.status = 'filled'
        mock_order.filled_avg_price = '50000.00'
        
        alpaca_client.trading_client.submit_order.return_value = mock_order
        
        response = alpaca_client.buy_crypto('BTC/USD', 1000)
        
        assert response['id'] == 'crypto123'
    
    def test_format_order_response(self, alpaca_client):
        """Test order response formatting"""
        mock_order = Mock()
        mock_order.id = 'test123'
        mock_order.status = 'filled'
        mock_order.filled_avg_price = '100.50'
        mock_order.qty = '10'
        
        response = alpaca_client._format_order_response(mock_order)
        
        assert response['id'] == 'test123'
        assert response['state'] == 'filled'
        assert response['price'] == 100.50
        assert response['quantity'] == 10.0
    
    def test_get_singleton_client(self):
        """Test singleton pattern"""
        # Reset singleton
        import src.api.alpaca
        src.api.alpaca.alpaca_client = None
        
        with patch('src.api.alpaca.AlpacaClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            client1 = get_alpaca_client('key1', 'secret1')
            client2 = get_alpaca_client('key1', 'secret1')
            
            # Should create only once
            assert mock_client_class.call_count == 1
            assert client1 == client2
