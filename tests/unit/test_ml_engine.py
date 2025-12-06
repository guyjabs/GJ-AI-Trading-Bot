"""
Unit tests for ML Engine module.
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from src.ml_engine import MLEngine
from unittest.mock import patch, MagicMock


class TestMLEngine:
    """Test suite for MLEngine"""
    
    @pytest.fixture
    def ml_engine(self, tmp_path, monkeypatch):
        """Create ML engine with temporary data directory"""
        test_file = str(tmp_path / "performance_history.json")
        test_weights_file = str(tmp_path / "strategy_weights.json")
        
        # Patch the module-level constants
        monkeypatch.setattr('src.ml_engine.PERFORMANCE_FILE', test_file)
        
        # Create engine
        engine = MLEngine()
        # Override file paths for testing
        engine.performance_history = []
        return engine
    
    def test_initialization(self, ml_engine):
        """Test ML engine initializes correctly"""
        # Weights might be loaded from file, so just check they exist and sum to ~1.0
        assert 'momentum' in ml_engine.strategy_weights
        assert 'growth' in ml_engine.strategy_weights
        assert 'value' in ml_engine.strategy_weights
        assert abs(sum(ml_engine.strategy_weights.values()) - 1.0) < 0.01
        assert isinstance(ml_engine.performance_history, list)
    
    def test_record_trade(self, ml_engine):
        """Test recording a trade"""
        ml_engine.record_trade(
            symbol='AAPL',
            decision='buy',
            quantity=10.0,
            entry_price=150.0,
            strategy='momentum'
        )
        
        assert len(ml_engine.performance_history) == 1
        trade = ml_engine.performance_history[0]
        assert trade['symbol'] == 'AAPL'
        assert trade['decision'] == 'buy'
        assert trade['quantity'] == 10.0
        assert trade['entry_price'] == 150.0
        assert trade['strategy'] == 'momentum'
        assert trade['closed'] == False  # Uses 'closed' not 'status'
    
    def test_close_trade_profit(self, ml_engine):
        """Test closing a trade with profit"""
        # Record buy
        ml_engine.record_trade('AAPL', 'buy', 10.0, 150.0, 'momentum')
        
        # Close with profit
        ml_engine.close_trade('AAPL', 160.0)
        
        trade = ml_engine.performance_history[0]
        assert trade['closed'] == True
        assert trade['exit_price'] == 160.0
        assert trade['profit_loss'] == 100.0  # (160-150) * 10
        assert trade['profit_loss_pct'] == pytest.approx(6.67, rel=0.01)  # ~6.67%
    
    def test_close_trade_loss(self, ml_engine):
        """Test closing a trade with loss"""
        ml_engine.record_trade('TSLA', 'buy', 5.0, 200.0, 'growth')
        ml_engine.close_trade('TSLA', 190.0)
        
        trade = ml_engine.performance_history[0]
        assert trade['profit_loss'] == -50.0  # (190-200) * 5
        assert trade['profit_loss_pct'] < 0
    
    def test_calculate_strategy_performance(self, ml_engine):
        """Test strategy performance calculation"""
        # Add some trades
        ml_engine.record_trade('AAPL', 'buy', 10.0, 150.0, 'momentum')
        ml_engine.close_trade('AAPL', 155.0)  # +$50
        
        ml_engine.record_trade('MSFT', 'buy', 5.0, 300.0, 'growth')
        ml_engine.close_trade('MSFT', 310.0)  # +$50
        
        ml_engine.record_trade('KO', 'buy', 20.0, 50.0, 'value')
        ml_engine.close_trade('KO', 48.0)  # -$40
        
        perf = ml_engine.calculate_strategy_performance(days=30)
        
        assert 'momentum' in perf
        assert 'growth' in perf
        assert 'value' in perf
        
        # Momentum should have 1 win
        assert perf['momentum']['num_trades'] == 1
        assert perf['momentum']['win_rate'] == 1.0
        
        # Value should have 1 loss
        assert perf['value']['num_trades'] == 1
        assert perf['value']['win_rate'] == 0.0
    
    def test_get_performance_summary(self, ml_engine):
        """Test performance summary generation"""
        # Add some trades
        ml_engine.record_trade('AAPL', 'buy', 10.0, 150.0, 'momentum')
        ml_engine.close_trade('AAPL', 155.0)
        
        ml_engine.record_trade('TSLA', 'buy', 5.0, 200.0, 'growth')
        ml_engine.close_trade('TSLA', 195.0)
        
        summary = ml_engine.get_performance_summary(days=30)
        
        assert summary['total_trades'] == 2
        assert summary['total_profit_loss'] == 25.0  # +50 -25
        assert 'overall_win_rate' in summary
        assert 'current_weights' in summary
        assert 'strategies' in summary  # Uses 'strategies' not 'strategy_performance'
    
    def test_no_trades_performance(self, ml_engine):
        """Test performance calculation with no trades"""
        perf = ml_engine.calculate_strategy_performance(days=30)
        
        # Returns empty dict when no trades
        assert perf == {}
    
    def test_empty_summary(self, ml_engine):
        """Test summary with no trades"""
        summary = ml_engine.get_performance_summary(days=30)
        
        assert summary['total_trades'] == 0
        assert summary['overall_win_rate'] == 0
        assert summary['total_profit_loss'] == 0
