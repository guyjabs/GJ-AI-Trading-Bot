import json
import re
from datetime import datetime
from src.utils.data_harness import compile_prompt_data
from src.api.openai import parse_ai_response

# Mock Objects for parsing test
class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)

class MockMessage:
    def __init__(self, content):
        self.content = content

class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]

def test_prompt_generation():
    print("Testing Prompt Generation...")
    
    # Mock Data
    account_info = {
        'buying_power': 10000.0,
        'portfolio_value': 25000.0,
        'portfolio_cash': 5000.0
    }
    
    portfolio_stocks = {
        'AAPL': {
            'quantity': 10,
            'price': 150.0,
            'average_buy_price': 140.0,
            'equity': 1500.0
        }
    }
    
    watchlist_overview = {
        'TSLA': {
            'price': 200.0,
            'rsi': 30.5,
            'vwap': 205.0,
            'sma_200': 190.0
        },
        'NVDA': {
            'price': 400.0,
            'rsi': 70.0,
            'vwap': 395.0,
            'sma_50': 380.0
        }
    }
    
    # Generate Data String
    data_string = compile_prompt_data(account_info, portfolio_stocks, watchlist_overview)
    print("\n generated Data String:\n")
    print(data_string)
    
    # Check if key elements are present
    assert "CURRENT MARKET STATE" in data_string
    assert "**TSLA**" in data_string
    assert "RSI (14): 30.5" in data_string
    assert "Unrealized PnL: 100.00" in data_string
    print("\n✅ Prompt Generation Test Passed!")

def test_response_parsing():
    print("\nTesting Response Parsing...")
    
    # Mock Response with Reasoning Trace
    mock_content = """
    Reasoning Trace:
    Analyzed AAPL: trend is bullish, RSI neutral. Holding is fine.
    Analyzed TSLA: RSI oversold, price below VWAP but above SMA200. Good entry.
    
    ```json
    [
      {
        "symbol": "TSLA",
        "decision": "buy",
        "quantity": 5,
        "reasoning": "RSI oversold",
        "stop_loss": 190.0,
        "profit_target": 220.0,
        "confidence": 0.85
      }
    ]
    ```
    """
    
    response = MockResponse(mock_content)
    decisions = parse_ai_response(response)
    
    print("\nParsed Decisions:", decisions)
    
    assert len(decisions) == 1
    assert decisions[0]['symbol'] == 'TSLA'
    assert decisions[0]['stop_loss'] == 190.0
    print("✅ Response Parsing Test Passed!")

def test_basic_mode_parsing():
    print("\nTesting Basic Mode Parsing (JSON Only)...")
    
    # Mock JSON-only response
    mock_content = """
    [
      {
        "symbol": "AAPL",
        "decision": "hold",
        "quantity": 0,
        "reasoning": "Waiting for dip"
      }
    ]
    """
    
    response = MockResponse(mock_content)
    decisions = parse_ai_response(response)
    
    print("\nParsed Decisions:", decisions)
    assert len(decisions) == 1
    assert decisions[0]['symbol'] == 'AAPL'
    print("✅ Basic Mode Parsing Test Passed!")

if __name__ == "__main__":
    test_prompt_generation()
    test_response_parsing()
    test_basic_mode_parsing()
