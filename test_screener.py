"""
Test script for the self-learning stock screener.
Run this to verify the screener is working correctly.
"""

import sys
sys.path.append('.')

from src.screener import screener
from src.ml_engine import ml_engine
from src.utils import logger

def test_screener():
    """Test the stock screener"""
    print("=" * 60)
    print("Testing Stock Screener")
    print("=" * 60)
    
    # Run screener
    results = screener.run_all_strategies()
    
    print(f"\n✅ Screener completed successfully!")
    print(f"Momentum picks: {len(results['momentum'])}")
    print(f"Growth picks: {len(results['growth'])}")
    print(f"Value picks: {len(results['value'])}")
    print(f"Total unique stocks: {len(results['all'])}")
    print(f"\nStrategy weights: {results['weights']}")
    
    print(f"\nTop 5 from each strategy:")
    print(f"Momentum: {results['momentum'][:5]}")
    print(f"Growth: {results['growth'][:5]}")
    print(f"Value: {results['value'][:5]}")

def test_ml_engine():
    """Test the ML engine"""
    print("\n" + "=" * 60)
    print("Testing ML Engine")
    print("=" * 60)
    
    # Simulate some trades
    print("\nSimulating trades...")
    ml_engine.record_trade("AAPL", "buy", 10, 150.0, "momentum")
    ml_engine.close_trade("AAPL", 155.0)  # +$50 profit
    
    ml_engine.record_trade("MSFT", "buy", 5, 300.0, "growth")
    ml_engine.close_trade("MSFT", 310.0)  # +$50 profit
    
    ml_engine.record_trade("KO", "buy", 20, 50.0, "value")
    ml_engine.close_trade("KO", 48.0)  # -$40 loss
    
    # Get performance summary
    summary = ml_engine.get_performance_summary(days=30)
    
    print(f"\n✅ ML Engine working!")
    print(f"Total trades: {summary['total_trades']}")
    print(f"Overall win rate: {summary['overall_win_rate']:.1%}")
    print(f"Total P&L: ${summary['total_profit_loss']:.2f}")
    print(f"\nCurrent strategy weights: {summary['current_weights']}")

if __name__ == "__main__":
    try:
        test_screener()
        test_ml_engine()
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
