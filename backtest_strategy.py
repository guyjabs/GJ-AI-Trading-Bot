
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.utils import logger

# Import Components
from config import ALPACA_CONFIG
from src.api.alpaca import get_alpaca_client
from src.backtester.engine import BacktestEngine

# Technical Analysis Helpers
def calculate_indicators(broker):
    """
    Calculate RSI and SMA for all symbols in the universe based on historical data up to current_time.
    """
    indicators = {}
    current_time = broker.current_time
    
    for symbol, df in broker.historical_data.items():
        # Get data up to current time
        # This is a simplification; in a real engine we'd step through index 
        # but here we just slice the DF up to current_date-1 or current_date
        
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        mask = df.index <= current_time
        data_so_far = df.loc[mask].copy()
        
        if len(data_so_far) < 200:
            continue
            
        # Calculate Indicators
        close = data_so_far['close']
        
        # SMA 200
        sma200 = close.rolling(window=200).mean().iloc[-1]
        
        # RSI 14
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]
        
        indicators[symbol] = {
            'price': close.iloc[-1],
            'sma200': sma200,
            'rsi': rsi_val
        }
        
    return indicators

# Global state for trailing stops
TRAILING_HIGHS = {}

def technical_strategy_rules(broker, timestamp):
    """
    Deterministic rules approximating the "Advanced" AI persona:
    1. Trend is King: Price > SMA 200
    2. Buy Weakness: RSI < 50 (Aggressive Entry in Uptrend)
    3. Sell Strength: RSI > 75 OR Trailing Stop Hit (-5% from High)
    """
    global TRAILING_HIGHS
    
    # 0. Portfolio State
    positions = broker.get_portfolio_stocks()
    cash = broker.get_account_info()['portfolio_cash']
    total_equity = broker.get_account_info()['portfolio_equity']
    
    # 1. Calculate Indicators
    indicators = calculate_indicators(broker)
    
    # Clean up trailing highs for closed positions
    current_symbols = set(positions.keys())
    for sym in list(TRAILING_HIGHS.keys()):
        if sym not in current_symbols:
            del TRAILING_HIGHS[sym]
            
    # 2. Strategy Logic
    for symbol in broker.historical_data.keys():
        if symbol not in indicators:
            continue
            
        data = indicators[symbol]
        price = data['price']
        sma200 = data['sma200']
        rsi = data['rsi']
        
        # Skip if data invalid
        if pd.isna(price) or pd.isna(sma200) or pd.isna(rsi):
            continue
            
        # --- SELL LOGIC ---
        if symbol in positions:
            pos = positions[symbol]
            
            # Update Trailing High
            if symbol not in TRAILING_HIGHS:
                TRAILING_HIGHS[symbol] = pos['average_buy_price']
            
            if price > TRAILING_HIGHS[symbol]:
                TRAILING_HIGHS[symbol] = price
                
            # Calculate Drawdown from High
            high = TRAILING_HIGHS[symbol]
            drawdown = (price - high) / high
            
            entry_price = pos['average_buy_price']
            pnl_pct = (price - entry_price) / entry_price
            
            # Rule: Sell if RSI Overbought OR Trailing Stop Hit
            if rsi > 75:
                broker.submit_order(symbol, pos['quantity'], 'sell')
                logger.info(f"SELL {symbol} Reason: MSI Overbought ({rsi:.2f})")
            elif drawdown < -0.05:
                broker.submit_order(symbol, pos['quantity'], 'sell')
                logger.info(f"SELL {symbol} Reason: Trailing Stop (-5% from ${high:.2f}) PnL: {pnl_pct*100:.1f}%")
            elif pnl_pct < -0.07: # Hard Stop vs Limit
                 broker.submit_order(symbol, pos['quantity'], 'sell')
                 logger.info(f"SELL {symbol} Reason: Hard Stop Loss (-7%)")

        # --- BUY LOGIC ---
        else:
            # Rule: Buy if Price > SMA200 (Uptrend) AND RSI < 50 (Aggressive Pullback)
            if price > sma200 and rsi < 50:
                # Allocation: Max 15% of Portfolio per trade ( Diversified)
                target_allocation = 0.15
                budget = total_equity * target_allocation
                
                # Check cash
                if cash > budget:
                    qty = int(budget / price)
                    if qty > 0:
                        broker.submit_order(symbol, qty, 'buy')
                        logger.info(f"BUY {symbol} Reason: Uptrend Pullback (RSI {rsi:.2f}, Price {price:.2f} > SMA {sma200:.2f})")

def main():
    print("\n" + "="*50)
    print("🚀 STARTING BACKTEST SIMULATION (OPTIMIZED)")
    print("Scenario: $10,000 Portfolio over Past 1 Year")
    print("Strategy: Trailing Stops + Aggressive RSI Entry")
    print("="*50 + "\n")

    # 1. Initialize Credentials
    api_key = ALPACA_CONFIG.get('api_key')
    secret_key = ALPACA_CONFIG.get('secret_key')
    paper = ALPACA_CONFIG.get('paper', True)
    
    if not api_key:
        print("Error: API Keys not found in config.py")
        return

    client = get_alpaca_client(api_key, secret_key, paper)
    
    # 2. Setup Backtest Engine
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    print(f"Fetching Data from Algebra: {start_date.date()} to {end_date.date()}")
    
    engine = BacktestEngine(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        initial_cash=10000.0,
        alpaca_client=client
    )
    
    # 3. Run Simulation
    # Expanded Universe
    engine.universe = ['NVDA', 'SPY', 'QQQ', 'AMD', 'MSFT', 'TSLA', 'COIN', 'GOOGL', 'AMZN', 'PLTR', 'META'] 
    
    engine.run(technical_strategy_rules)
    
    print("\n✅ Simulation Complete.")

if __name__ == "__main__":
    main()
