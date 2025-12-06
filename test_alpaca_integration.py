import sys
import os
from src.api.alpaca import get_alpaca_client
from config import ALPACA_CONFIG

def test_alpaca_connection():
    print("Testing Alpaca Connection...")
    try:
        client = get_alpaca_client(
            api_key=ALPACA_CONFIG.get('api_key'),
            secret_key=ALPACA_CONFIG.get('secret_key'),
            paper=ALPACA_CONFIG.get('paper', True)
        )
        
        account = client.get_account_info()
        print(f"✅ Connection Successful!")
        print(f"   Buying Power: ${account.get('buying_power', 0):.2f}")
        print(f"   Portfolio Value: ${account.get('portfolio_value', 0):.2f}")
        return True
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return False

def test_market_data():
    print("\nTesting Market Data...")
    try:
        client = get_alpaca_client()
        price = client.get_current_price("AAPL")
        print(f"✅ AAPL Price: ${price:.2f}")
        
        hist = client.get_historical_data("AAPL", span="day")
        if not hist.empty:
            print(f"✅ Historical Data: {len(hist)} bars received")
        else:
            print("⚠️ Historical Data: No data received (Market might be closed or span issue)")
            
        return True
    except Exception as e:
        print(f"❌ Market Data Failed: {e}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("🦙 ALPACA INTEGRATION TEST")
    print("="*50)
    
    conn_success = test_alpaca_connection()
    data_success = test_market_data()
    
    if conn_success and data_success:
        print("\n✨ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n💥 SOME TESTS FAILED")
        sys.exit(1)
