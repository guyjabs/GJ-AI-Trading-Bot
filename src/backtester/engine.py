from datetime import timedelta
import pandas as pd
import yfinance as yf
from src.utils import logger
from .broker_mock import MockBroker

class BacktestEngine:
    def __init__(self, start_date, end_date, initial_cash=100000):
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        self.broker = MockBroker(initial_cash)
        self.universe = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'SPY'] # Default universe
        
    def load_data(self):
        """Fetch historical data for universe"""
        logger.info("Fetching historical data...")
        data_cache = {}
        for symbol in self.universe:
            try:
                # Add buffer for indicators
                start = self.start_date - timedelta(days=60)
                df = yf.download(symbol, start=start, end=self.end_date, progress=False)
                if not df.empty:
                    data_cache[symbol] = df
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
        
        self.broker.set_data(data_cache)
        logger.info(f"Loaded data for {len(data_cache)} symbols")

    def run(self, strategy_callback):
        """
        Run the simulation.
        strategy_callback(broker, timestamp): Function called on every tick
        """
        # Ensure we have data
        if not self.broker.historical_data:
            self.load_data()
            
        # Generate timeline (Daily bars for now, at market close)
        # Using SPY as calendar reference
        spy_data = self.broker.historical_data.get('SPY')
        if spy_data is None:
             logger.error("No SPY data to sync timeline")
             return

        timeline = spy_data.index[spy_data.index >= self.start_date]
        
        logger.info(f"Starting Backtest: {len(timeline)} periods")
        
        for timestamp in timeline:
            # Update Broker Time
            self.broker.update_time(timestamp)
            
            # Run Strategy
            try:
                strategy_callback(self.broker, timestamp)
            except Exception as e:
                logger.error(f"Strategy Error at {timestamp}: {e}")
                
        self._generate_report()

    def _generate_report(self):
        stats = self.get_stats()
        print("\n=== BACKTEST RESULTS ===")
        print(f"Start Date: {self.start_date.date()}")
        print(f"End Date: {self.end_date.date()}")
        print(f"Initial Cash: ${self.broker.initial_cash:,.2f}")
        print(f"Final Equity: ${stats['final_equity']:,.2f}")
        print(f"Total Return: {stats['return_pct']:.2f}%")
        print(f"Total Trades: {len(self.broker.orders)}")
        print("========================\n")

    def get_stats(self):
        if not self.broker.equity_curve:
            return {}
        
        initial = self.broker.initial_cash
        final = self.broker.equity_curve[-1]['equity']
        return {
            'final_equity': final,
            'return_pct': ((final - initial) / initial) * 100,
            'equity_curve': self.broker.equity_curve
        }
