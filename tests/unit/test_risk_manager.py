"""
Unit tests for RiskManager module.
"""

import pytest
from src.risk_manager import RiskManager


class TestRiskManager:
    """Test suite for RiskManager"""
    
    def test_initialization(self):
        """Test RiskManager initializes with correct defaults"""
        rm = RiskManager()
        assert rm.stop_loss_pct == 0.05
        assert rm.take_profit_pct == 0.10
        assert rm.max_daily_loss_pct == 0.02
        assert rm.trading_halted == False
    
    def test_set_starting_balance(self):
        """Test setting starting balance"""
        rm = RiskManager()
        rm.set_starting_balance(10000.0)
        assert rm.daily_starting_balance == 10000.0
        assert rm.trading_halted == False
    
    def test_portfolio_health_check_healthy(self):
        """Test portfolio health check when within limits"""
        rm = RiskManager()
        rm.set_starting_balance(10000.0)
        
        # Loss of 1% (within 2% limit)
        current_balance = 9900.0
        assert rm.check_portfolio_health(current_balance) == True
        assert rm.trading_halted == False
    
    def test_portfolio_health_check_circuit_breaker(self):
        """Test circuit breaker triggers on excessive loss"""
        rm = RiskManager()
        rm.set_starting_balance(10000.0)
        
        # Loss of 3% (exceeds 2% limit)
        current_balance = 9700.0
        assert rm.check_portfolio_health(current_balance) == False
        assert rm.trading_halted == True
    
    def test_stop_loss_trigger(self):
        """Test stop loss detection"""
        rm = RiskManager(stop_loss_pct=0.05)
        
        # 6% drop should trigger stop loss
        result = rm.check_position_risk(
            symbol='AAPL',
            current_price=94.0,
            avg_buy_price=100.0,
            quantity=10.0
        )
        assert result == 'sell_stop_loss'
    
    def test_take_profit_trigger(self):
        """Test take profit detection"""
        rm = RiskManager(take_profit_pct=0.10)
        
        # 11% gain should trigger take profit
        result = rm.check_position_risk(
            symbol='AAPL',
            current_price=111.0,
            avg_buy_price=100.0,
            quantity=10.0
        )
        assert result == 'sell_take_profit'
    
    def test_position_safe(self):
        """Test position within safe range"""
        rm = RiskManager()
        
        # 3% gain (below 10% take profit)
        result = rm.check_position_risk(
            symbol='AAPL',
            current_price=103.0,
            avg_buy_price=100.0,
            quantity=10.0
        )
        assert result is None
    
    def test_monitor_positions(self, sample_portfolio):
        """Test monitoring multiple positions"""
        rm = RiskManager(stop_loss_pct=0.05, take_profit_pct=0.10)
        
        # TSLA is down 9% (should trigger stop loss)
        actions = rm.monitor_positions(sample_portfolio)
        
        assert len(actions) == 1
        assert actions[0]['symbol'] == 'TSLA'
        assert actions[0]['action'] == 'sell'
        assert actions[0]['reason'] == 'sell_stop_loss'
    
    def test_calculate_position_size(self):
        """Test position sizing calculation"""
        rm = RiskManager()
        rm.set_starting_balance(10000.0)
        
        # Risk 1% on a $5 stop
        shares = rm.calculate_position_size_by_risk(
            entry_price=100.0,
            stop_price=95.0,
            risk_pct=1.0
        )
        
        # $10,000 * 1% = $100 risk / $5 per share = 20 shares
        assert shares == 20
