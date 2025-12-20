from src.backtester.engine import BacktestEngine
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)

def simple_strategy(broker, timestamp):
    # Determine what to do at this timestamp
    # Simple Buy and Hold SPY
    
    symbol = 'SPY'
    account = broker.get_account_info()
    cash = account['portfolio_cash']
    
    portfolio = broker.get_portfolio_stocks()
    
    if symbol not in portfolio and cash > 1000:
        # Buy as much as possible
        price = broker.get_current_price(symbol)
        if price:
            qty = int(cash * 0.95 / price) # 95% cash use
            if qty > 0:
                broker.submit_order(symbol, qty, 'buy')

def main():
    print("🚀 Starting Backtest Verification...")
    
    # Run last 30 days
    bt = BacktestEngine(start_date='2024-01-01', end_date='2024-03-01', initial_cash=100000)
    bt.universe = ['SPY'] # Only load SPY to be fast
    
    bt.run(simple_strategy)
    
    print("✅ Backtest Complete")

if __name__ == "__main__":
    main()
