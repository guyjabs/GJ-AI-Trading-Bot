import time
from datetime import datetime
from src.utils import logger
from src.config_manager import config_manager
from src.risk_manager import risk_manager
from src.notifications import notifier
from src.screener import screener
from src.ml_engine import ml_engine
from src.api.alpaca import get_alpaca_client, alpaca_client
from config import ALPACA_CONFIG
from src.ai.brain import AIBrain
from src.ai.macro_analyst import MacroAnalyst
from src.ai.fundamentalist import Fundamentalist
from src.execution.executor import TradeExecutor

class TradingBot:
    """
    Central Orchestrator for the GJ AI Trading Bot.
    Manages the lifecycle: Health Check -> Screen -> Analyze -> Execute.
    """
    def __init__(self):
        logger.info("🤖 Initializing GJ AI Trading Bot (Modular)...")
        
        # 1. Initialize API Client
        self.client = get_alpaca_client(
            api_key=ALPACA_CONFIG['api_key'],
            secret_key=ALPACA_CONFIG['secret_key'],
            paper=ALPACA_CONFIG.get('paper', True)
        )
        
        # 2. Initialize Components
        self.brain = AIBrain()
        self.macro = MacroAnalyst()
        self.fund = Fundamentalist()
        self.executor = TradeExecutor(self.client)
        
        # Ensure singletons are ready
        # risk_manager, screener, etc are imported singletons
        
    def run_cycle(self, progress_callback=None):
        """
        Executes one full trading cycle.
        """
        logger.info("--- Starting Trading Cycle ---")
        
        def report(text, pct, status='in-progress'):
            if progress_callback: progress_callback(text, pct, status)
            
        # 1. Risk Management (Circuit Breaker)
        report("Checking Portfolio Health...", 10)
        account = self.client.get_account_info()
        portfolio_value = account['portfolio_value']
        
        if not risk_manager.check_portfolio_health(portfolio_value):
            logger.error("🚨 CIRCUIT BREAKER TRIPPED. HALTING.")
            notifier.notify_error("Circuit Breaker Tripped. Trading Halted.")
            return

        # 2. Manage Existing Positions (Stop Loss/Take Profit)
        report("Managing Positions...", 20)
        positions = self.client.get_portfolio_stocks() # Includes crypto if adapted
        risk_actions = risk_manager.monitor_positions(positions)
        for action in risk_actions:
            self.executor.execute_risk_action(action)
            
        # 3. Macro Analysis (Soros)
        report("Analyzing Macro Regime...", 30)
        macro_context = self.macro.analyze_macro_context()
        logger.info(f"🌍 Macro Regime: {macro_context.get('regime')} (VIX: {macro_context.get('vix')})")
            
        # 4. Screener
        report("Screening Market...", 40)
        # screener.run_screener() returns dict with 'momentum', 'growth', etc.
        screen_results = screener.run_screener()
        candidates = self._compile_candidates(screen_results)
        
        if not candidates:
            logger.info("No candidates found.")
            return

        # 5. Data Gathering (Technicals + Fundamentals)
        report("Gathering Data...", 60)
        market_data, fund_data = self._gather_data(candidates)
        
        # 6. ML Learning (Optional Update)
        try:
             ml_engine.learn_and_adjust()
        except:
             pass

        # 7. AI Analysis (The Brain)
        report("AI Analyzing...", 80)
        decisions = self.brain.analyze(
            account_info=account,
            portfolio=positions,
            candidates=market_data,
            macro_context=macro_context,
            fundamental_data=fund_data
        )
        
        # 8. Execution (The Executor)
        report("Executing Trades...", 90)
        for decision in decisions:
            self.executor.execute_decision(decision, account, market_data)
            
        report("Cycle Complete", 100, 'done')
        
    def _compile_candidates(self, results):
        """Flatten screener results into a list of symbols."""
        stocks = results.get('momentum', [])[:5] + \
                 results.get('growth', [])[:3] + \
                 results.get('value', [])[:2]
        
        crypto = results.get('crypto', [])
        if isinstance(crypto, dict):
            flat_crypto = []
            for picks in crypto.values():
                flat_crypto.extend(picks)
            crypto = flat_crypto
        
        return list(set(stocks + crypto[:5]))

    def _gather_data(self, symbols):
        """Gather price, technicals, and fundamentals for candidates."""
        data = {}
        fundamentals = {} # Map symbol -> dict
        
        for sym in symbols:
            try:
                # Basic mock or real fetch - Executor or Bot needs data
                # For now using client methods.
                # Detect type (simple heuristic or lookup)
                is_crypto = sym.endswith('USD') or len(sym) > 5 # Rough heuristic
                
                if is_crypto:
                     quote = self.client.get_crypto_quote(sym)
                     price = float(quote['mark_price'])
                     data[sym] = {'price': price, 'type': 'crypto'}
                else:
                     # STOCK
                     price = self.client.get_current_price(sym)
                     if price > 0:
                         # Fetch history for RSI
                         params = self.client.get_historical_data(sym, interval="5minute", span="day")
                         info = {'price': price, 'type': 'stock'}
                         info = self.client.enrich_with_rsi(info, params, sym)
                         data[sym] = info
                         
                         # FUNDAMENTALS (Lynch)
                         fundamentals[sym] = self.fund.get_fundamentals(sym)
                         
            except Exception as e:
                logger.error(f"Data error {sym}: {e}")
        return data, fundamentals
