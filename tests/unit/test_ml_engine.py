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
    def ml_engine(self, monkeypatch):
        """Create ML engine with mocked DB"""
        # Mock the db module in src.ml_engine
        mock_db = MagicMock()
        monkeypatch.setattr('src.ml_engine.db', mock_db)
        
        # Setup mock returns
        mock_db.load_latest_weights.return_value = {
            'momentum': 0.33,
            'growth': 0.33,
            'value': 0.34
        }
        # Default empty history
        mock_db.get_performance_history.return_value = []
        
        # Internal performance_history list tracking for the test instance
        # Since the real engine creates this from DB, we simulate it
        engine = MLEngine()
        # We need to manually intercept record/close calls if we want to test state
        # Or we can just check if db methods were called.
        # But the existing tests check 'engine.performance_history' list.
        # We need to adapt the tests or the engine.
        # The engine logic: record_trade -> db.record_entry.
        # The engine logic: calculate_strategy_performance -> db.get_performance_history.
        # The OLD tests assumed in-memory list. The NEW engine relies on DB.
        
        # To make old tests pass with minimal changes, we can mock 
        # get_performance_history to return what we want.
        
        return engine, mock_db

    def test_initialization(self, ml_engine):
        """Test ML engine initializes correctly"""
        engine, mock_db = ml_engine
        # Weights might be loaded from file, so just check they exist and sum to ~1.0
        assert 'momentum' in engine.strategy_weights
        assert 'growth' in engine.strategy_weights
        assert 'value' in engine.strategy_weights
        assert abs(sum(engine.strategy_weights.values()) - 1.0) < 0.01
        
        # Verify DB load was called
        mock_db.load_latest_weights.assert_called_once()
    
    def test_record_trade(self, ml_engine):
        """Test recording a trade"""
        engine, mock_db = ml_engine
        engine.record_trade(
            symbol='AAPL',
            decision='buy',
            quantity=10.0,
            entry_price=150.0,
            strategy='momentum'
        )
        
        # Check DB call
        mock_db.record_entry.assert_called_once()
        call_args = mock_db.record_entry.call_args[0][0]
        assert call_args['symbol'] == 'AAPL'
        assert call_args['entry_price'] == 150.0
        assert call_args['quantity'] == 10.0
        assert call_args['strategy'] == 'momentum'
    
    def test_close_trade_profit(self, ml_engine):
        """Test closing a trade with profit"""
        engine, mock_db = ml_engine
        
        # Setup mock return for record_exit
        mock_db.record_exit.return_value = {
            'profit_loss': 100.0,
            'profit_loss_pct': 6.67
        }
        
        # Close with profit
        engine.close_trade('AAPL', 160.0)
        
        # Check DB call
        mock_db.record_exit.assert_called_with('AAPL', 160.0)
    
    def test_close_trade_loss(self, ml_engine):
        """Test closing a trade with loss"""
        engine, mock_db = ml_engine
        
        mock_db.record_exit.return_value = {
            'profit_loss': -50.0,
            'profit_loss_pct': -5.0
        }
        
        engine.close_trade('TSLA', 190.0)
        
        # Check DB call
        mock_db.record_exit.assert_called_with('TSLA', 190.0)
    
    def test_calculate_strategy_performance(self, ml_engine):
        """Test strategy performance calculation"""
        engine, mock_db = ml_engine
        
        # Mock history returned by DB
        # Note: calculated_strategy_performance filters for closed trades
        mock_db.get_performance_history.return_value = [
            {'strategy': 'momentum', 'profit_loss': 50.0, 'profit_loss_pct': 5.0, 'is_closed': 1, 'exit_date': datetime.now().isoformat(), 'hold_duration_hours': 1},
            {'strategy': 'growth', 'profit_loss': 50.0, 'profit_loss_pct': 5.0, 'is_closed': 1, 'exit_date': datetime.now().isoformat(), 'hold_duration_hours': 1},
            {'strategy': 'value', 'profit_loss': -40.0, 'profit_loss_pct': -4.0, 'is_closed': 1, 'exit_date': datetime.now().isoformat(), 'hold_duration_hours': 1},
        ]
        
        perf = engine.calculate_strategy_performance(days=30)
        
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
        engine, mock_db = ml_engine
        
        mock_db.get_performance_history.return_value = [
            {'strategy': 'momentum', 'profit_loss': 50.0, 'profit_loss_pct': 5.0, 'is_closed': 1, 'exit_date': datetime.now().isoformat(), 'hold_duration_hours': 1},
            {'strategy': 'growth', 'profit_loss': -25.0, 'profit_loss_pct': -2.5, 'is_closed': 1, 'exit_date': datetime.now().isoformat(), 'hold_duration_hours': 1},
        ]
        
        summary = engine.get_performance_summary(days=30)
        
        assert summary['total_trades'] == 2
        assert summary['total_profit_loss'] == 25.0  # +50 -25
        assert 'overall_win_rate' in summary
        assert 'current_weights' in summary
        assert 'strategies' in summary
    
    def test_no_trades_performance(self, ml_engine):
        """Test performance calculation with no trades"""
        engine, mock_db = ml_engine
        mock_db.get_performance_history.return_value = []
        
        perf = engine.calculate_strategy_performance(days=30)
        
        # Returns empty dict when no trades
        assert perf == {}
    
    def test_empty_summary(self, ml_engine):
        """Test summary with no trades"""
        engine, mock_db = ml_engine
        mock_db.get_performance_history.return_value = []
        
        summary = engine.get_performance_summary(days=30)
        
        assert summary['total_trades'] == 0
        assert summary['overall_win_rate'] == 0
        assert summary['total_profit_loss'] == 0
