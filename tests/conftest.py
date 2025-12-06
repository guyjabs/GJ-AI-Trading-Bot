"""
Pytest configuration and shared fixtures for testing.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime


@pytest.fixture
def mock_alpaca_client():
    """Mock Alpaca client for testing"""
    client = Mock()
    
    # Mock account info
    client.get_account_info.return_value = {
        'buying_power': 10000.0,
        'portfolio_cash': 5000.0,
        'portfolio_equity': 15000.0,
        'portfolio_value': 20000.0
    }
    
    # Mock portfolio
    client.get_portfolio_stocks.return_value = {
        'AAPL': {
            'quantity': 10.0,
            'price': 150.0,
            'average_buy_price': 140.0,
            'equity': 1500.0,
            'type': 'stock',
            'name': 'Apple Inc.'
        }
    }
    
    # Mock crypto positions
    client.get_crypto_positions.return_value = []
    
    # Mock market status
    client.is_market_open.return_value = True
    
    # Mock price data
    client.get_current_price.return_value = 150.0
    
    return client


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing screener"""
    return {
        'AAPL': {
            'symbol': 'AAPL',
            'current_price': 150.0,
            'market_cap': 2_500_000_000_000,
            'avg_volume': 50_000_000,
            'price_change_5d': 5.5,
            'volume_ratio': 2.5,
            '50day_avg': 145.0,
            'pct_from_52week_high': -5.0,
            'revenue_growth': 0.20,
            'earnings_growth': 0.15,
            'pe_ratio': 25.0,
            'pb_ratio': 30.0
        },
        'TSLA': {
            'symbol': 'TSLA',
            'current_price': 200.0,
            'market_cap': 600_000_000_000,
            'avg_volume': 100_000_000,
            'price_change_5d': 10.0,
            'volume_ratio': 3.0,
            '50day_avg': 180.0,
            'pct_from_52week_high': -2.0,
            'revenue_growth': 0.30,
            'earnings_growth': 0.25,
            'pe_ratio': 50.0,
            'pb_ratio': 15.0
        }
    }


@pytest.fixture
def sample_portfolio():
    """Sample portfolio for testing risk manager"""
    return {
        'AAPL': {
            'quantity': 10.0,
            'price': 150.0,
            'average_buy_price': 140.0
        },
        'TSLA': {
            'quantity': 5.0,
            'price': 200.0,
            'average_buy_price': 220.0
        }
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        'choices': [{
            'message': {
                'content': '{"decision": "buy", "symbol": "AAPL", "quantity": 10, "reasoning": "Strong momentum"}'
            }
        }]
    }
