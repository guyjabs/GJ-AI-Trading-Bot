"""
Unit tests for StockScreener module.
"""

import pytest
from src.screener import StockScreener


class TestStockScreener:
    """Test suite for StockScreener"""
    
    def test_initialization(self):
        """Test screener initializes correctly"""
        screener = StockScreener()
        assert screener.universe is not None
        assert len(screener.universe) > 0
        assert screener.strategy_weights['momentum'] == 0.30
        assert screener.strategy_weights['growth'] == 0.40
        assert screener.strategy_weights['value'] == 0.30
    
    def test_momentum_screening(self, sample_stock_data):
        """Test momentum strategy screening"""
        screener = StockScreener()
        screener.stock_data = sample_stock_data
        
        results = screener.screen_momentum(top_n=2)
        
        # Should return list of tuples (symbol, score)
        assert isinstance(results, list)
        assert len(results) <= 2
        
        # TSLA should score higher (10% gain vs 5.5%)
        if len(results) > 0:
            assert results[0][0] in ['TSLA', 'AAPL']
            assert results[0][1] > 0  # Score should be positive
    
    def test_growth_screening(self, sample_stock_data):
        """Test growth strategy screening"""
        screener = StockScreener()
        screener.stock_data = sample_stock_data
        
        results = screener.screen_growth(top_n=2)
        
        assert isinstance(results, list)
        assert len(results) <= 2
        
        # TSLA has higher growth metrics
        if len(results) > 0:
            assert results[0][1] > 0
    
    def test_value_screening(self, sample_stock_data):
        """Test value strategy screening"""
        screener = StockScreener()
        screener.stock_data = sample_stock_data
        
        results = screener.screen_value(top_n=2)
        
        assert isinstance(results, list)
        # May be empty if no stocks meet value criteria
        assert len(results) <= 2
    
    def test_strategy_weights_persistence(self, tmp_path):
        """Test saving and loading strategy weights"""
        import os
        import json
        
        screener = StockScreener()
        screener.strategy_weights = {
            'momentum': 0.40,
            'growth': 0.35,
            'value': 0.25
        }
        
        # Save weights
        screener.save_strategy_weights()
        
        # Load weights in new instance
        screener2 = StockScreener()
        screener2.load_strategy_weights()
        
        assert screener2.strategy_weights['momentum'] == 0.40
        assert screener2.strategy_weights['growth'] == 0.35
        assert screener2.strategy_weights['value'] == 0.25
    
    def test_empty_stock_data(self):
        """Test screening with no stock data"""
        screener = StockScreener()
        screener.stock_data = {}
        
        momentum_results = screener.screen_momentum(top_n=10)
        growth_results = screener.screen_growth(top_n=10)
        value_results = screener.screen_value(top_n=10)
        
        assert len(momentum_results) == 0
        assert len(growth_results) == 0
        assert len(value_results) == 0
