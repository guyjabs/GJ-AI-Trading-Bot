from src.data.intraday_data import intraday_data
import pandas as pd

def test_fetch():
    symbol = "TSLA"
    print(f"Testing fetch for {symbol}...")
    
    # Test 1: Intraday 1d
    print("\n--- Test 1: get_intraday_data (1d) ---")
    df = intraday_data.get_intraday_data(symbol, interval="1d", period="5d")
    print(f"Result empty: {df.empty}")
    if not df.empty:
        print(df.tail())
        print(f"Current Price from df: {df['Close'].iloc[-1]}")
    
    # Test 2: Intraday 5m
    print("\n--- Test 2: get_intraday_data (5m) ---")
    df_5m = intraday_data.get_intraday_data(symbol, interval="5m", period="1d")
    print(f"Result empty: {df_5m.empty}")
    if not df_5m.empty:
        print(df_5m.tail())
    
    # Test 3: Premarket Gap
    print("\n--- Test 3: get_premarket_gap ---")
    gap = intraday_data.get_premarket_gap(symbol)
    print(f"Gap: {gap}")

if __name__ == "__main__":
    test_fetch()
