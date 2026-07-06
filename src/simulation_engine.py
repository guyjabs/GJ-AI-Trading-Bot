import pandas as pd
from datetime import datetime, timedelta
from src.utils import logger
from config import ALPACA_CONFIG
from src.api.alpaca import get_alpaca_client
from src.backtester.engine import BacktestEngine
from src.ml_engine import ml_engine

def calculate_indicators(broker):
    """
    Calculate RSI and SMA for all symbols in the universe based on historical data up to current_time.
    (Duplicated from backtest_strategy for independence, can be refactored to common utils later)
    """
    indicators = {}
    current_time = broker.current_time
    
    for symbol, df in broker.historical_data.items():
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        mask = df.index <= current_time
        data_so_far = df.loc[mask].copy()
        
        if len(data_so_far) < 200:
            if len(df) > 0:
                 logger.warning(f"⚠️ {symbol}: insufficient history ({len(data_so_far)} < 200). Data range: {df.index[0]} to {df.index[-1]}. Current time: {current_time}")
            else:
                 logger.warning(f"⚠️ {symbol}: Empty dataframe")
            continue
            
        close = data_so_far['close']
        current_price = close.iloc[-1]
        
        # SMA 200 & 50
        sma200 = close.rolling(window=200).mean().iloc[-1]
        sma50 = close.rolling(window=50).mean().iloc[-1]
        
        # RSI 14
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]
        
        # logger.info(f"debug: {symbol} price={current_price:.2f} rsi={rsi_val:.2f}")
        
        indicators[symbol] = {
            'price': current_price,
            'sma200': sma200,
            'sma50': sma50,
            'rsi': rsi_val
        }
        
    return indicators

from main2 import get_ai_decisions
from src.research.news_aggregator import NewsAggregator

# Initialize News Aggregator for Simulation
news_agg = NewsAggregator(
    newsapi_key=ALPACA_CONFIG.get('newsapi_key'), # Ensure these are in config
    alphavantage_key=ALPACA_CONFIG.get('alphavantage_key'),
    finnhub_key=ALPACA_CONFIG.get('finnhub_key')
)

def ai_simulation_strategy(broker, timestamp):
    """
    Realistic Simulation Strategy:
    1. Fetch Historical News for 'timestamp'
    2. Get AI Decision using main2.py logic (OpenAI)
    3. Execute Trades
    """
    # 1. Prepare Context
    current_date = pd.to_datetime(timestamp).date()
    
    # Portfolio Overview
    positions = broker.get_portfolio_stocks()
    account = broker.get_account_info()
    
    # Helper to fetch and format timezone-aligned history slice for indicators calculation
    def get_history_slice(symbol):
        df = broker.historical_data.get(symbol)
        if df is not None:
            mask = df.index <= broker.current_time
            slice_df = df.loc[mask].copy()
            rename_map = {
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }
            return slice_df.rename(columns={k: v for k, v in rename_map.items() if k in slice_df.columns})
        return None

    # Watchlist Overview (Current Prices + Indicators)
    indicators = calculate_indicators(broker)
    watchlist_overview = {}
    for symbol, data in indicators.items():
        watchlist_overview[symbol] = {
            'price': data['price'],
            'current_price': data['price'],
            'sma200': data['sma200'],
            'rsi': data['rsi'],
            'type': 'stock',
            'history': get_history_slice(symbol)
        }
    
    # Simple formatting for portfolio overview
    portfolio_overview = {}
    for sym, pos in positions.items():
        portfolio_overview[sym] = {
            'quantity': pos['quantity'],
            'average_buy_price': pos['average_buy_price'],
            'equity': pos['quantity'] * indicators.get(sym, {}).get('price', 0),
            'price': indicators.get(sym, {}).get('price', 0),
            'history': get_history_slice(sym)
        }

    # 2. Fetch Historical News
    # Note: timestamp is a Pandas Timestamp, convert to datetime
    news_context = news_agg.get_news_for_date(current_date)
    
    # 3. Ask OpenAI
    try:
        decisions = get_ai_decisions(
            context_date=current_date,
            account_info=account,
            portfolio_overview=portfolio_overview,
            watchlist_overview=watchlist_overview,
            predictions=[], # Predictions hard to backfill without saving them
            risk_constraints=[],
            news_context=news_context
        )
        
        # 4. Execute Decisions
        for d in decisions:
            symbol = d.get('symbol')
            # STRICT UNIVERSE CHECK
            if symbol not in broker.universe:
                logger.warning(f"🚫 AI Hallucination: {symbol} not in universe {broker.universe}. Skipping.")
                continue

            action = d.get('decision')
            quantity = d.get('quantity', 0)
            
            if action == 'buy':
                # Re-check cash in case AI hallucinated
                price = indicators.get(symbol, {}).get('price', 0)
                if price <= 0:
                     logger.warning(f"⚠️ Price 0 for {symbol}, skipping buy.")
                     continue
                
                # RUTHLESS SIZING LOGIC FOR SIMULATION
                conviction = float(d.get('conviction', 5.0))
                conviction = max(1.0, min(10.0, conviction))
                
                buying_power = account['portfolio_cash'] # In sim, cash is buying power
                max_allocation_usd = buying_power * 0.20
                trade_allocation_usd = max_allocation_usd * (conviction / 10.0)
                
                if trade_allocation_usd < 100:
                    continue
                    
                quantity = int(trade_allocation_usd / price)
                     
                cost = price * quantity
                if account['portfolio_cash'] >= cost and quantity > 0:
                     broker.submit_order(symbol, quantity, 'buy')
                     logger.info(f"🤖 AI SIM BUY {symbol}: {quantity} @ {price:.2f} (C:{conviction}, ${cost:.2f})")
            
            elif action == 'sell':
                if symbol in positions:
                    # Validate quantity
                    qty_owned = positions[symbol]['quantity']
                    # Sell full position if conviction is high or not specified?
                    # The prompt says "sell means close/reduce". 
                    # Let's assume sell = CLOSE FULL POSITION for now to be ruthless.
                    # Or use conviction to scale out.
                    
                    broker.submit_order(symbol, qty_owned, 'sell')
                    logger.info(f"🤖 AI SIM SELL {symbol}: {qty_owned}")
                        
    except Exception as e:
        logger.error(f"AI Simulation Error on {current_date}: {e}")

class SimulatorEngine:
    def __init__(self, start_date, end_date, initial_cash, universe):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        self.universe = universe
        
        # Init Alpaca
        api_key = ALPACA_CONFIG.get('api_key')
        secret_key = ALPACA_CONFIG.get('secret_key')
        paper = ALPACA_CONFIG.get('paper', True)
        self.client = get_alpaca_client(api_key, secret_key, paper)
        
    def run(self):
        """Run the simulation and return results"""
        
        logger.info(f"Starting Simulation: {self.start_date} -> {self.end_date}, ${self.initial_cash}")
        
        # 1. Setup Engine
        engine = BacktestEngine(
            start_date=self.start_date,
            end_date=self.end_date,
            initial_cash=self.initial_cash,
        )
        # Ensure SPY is in the backtester universe for timeline calendar reference
        engine.universe = list(set(self.universe + ['SPY']))
        
        # 2. Get Current Weights (Logging only, not used in AI logic)
        current_weights = ml_engine.strategy_weights
        logger.info(f"Starting Realistic AI Simulation ({self.start_date} to {self.end_date})")
        
        # Monkey-patch universe into broker for the strategy to use
        engine.broker.universe = self.universe
        
        # 3. Define Strategy Callback
        # We pass the function directly
            
        # 4. Run
        engine.run(ai_simulation_strategy)
        
        # 5. Format Results
        stats = engine.get_stats()
        
        return {
            'final_balance': stats.get('final_equity', self.initial_cash),
            'total_return_pct': stats.get('return_pct', 0.0),
            'equity_curve': stats.get('equity_curve', []),
            'trades': len(engine.broker.orders),
            'strategy_weights': current_weights
        }
