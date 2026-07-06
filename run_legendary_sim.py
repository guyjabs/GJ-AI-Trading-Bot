
import os
import sys
import asyncio
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from openai import AsyncOpenAI
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(os.getcwd())

# Import Bot Components
from config import OPENAI_API_KEY, ALPACA_CONFIG, OPENAI_MODEL_NAME
from src.ai.brain import AIBrain
from src.utils.data_harness import compile_prompt_data
from src.api.alpaca import get_alpaca_client
from src.backtester.engine import BacktestEngine
from src.simulation_engine import calculate_indicators
from src.ai.fundamentalist import Fundamentalist

# Initialize Async Client
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def fetch_legendary_decision(date, brain, account, portfolio, market_data, macro_context, fund_data, sem):
    """
    Async wrapper for the AIBrain logic using AsyncOpenAI.
    """
    async with sem:
        try:
            # Reconstruct the exact prompt the Bot would use
            prompt = brain._build_alpha_predator_prompt(
                date, account, portfolio, market_data, macro_context, fund_data
            )
            
            # Call Async API
            response = await aclient.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON (Simplistic parser for sim)
            import re
            json_match = re.search(r'```json\s*(.*?)```', content, re.DOTALL)
            decisions = []
            if json_match:
                decisions = json.loads(json_match.group(1))
            else:
                bracket_match = re.search(r'(\[.*\])', content, re.DOTALL)
                if bracket_match:
                    decisions = json.loads(bracket_match.group(1))
            
            return {
                'date': date,
                'prompt': prompt, # debug
                'decisions': decisions,
                'raw_response': content
            }
            
        except Exception as e:
            # logger.error(f"Error on {date}: {e}")
            return {'date': date, 'decisions': [], 'error': str(e)}

async def run_legendary_sim():
    print("=== Starting LEGENDARY 1-Year Simulation (Macro + Fundamental + Tech) ===")
    
    # 1. Configuration
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    universe = ['AAPL', 'MSFT', 'SPY', 'NVDA', 'TSLA'] # Top Conviction Names
    
    # 2. Setup Backtest Engine (Data)
    client = get_alpaca_client(ALPACA_CONFIG['api_key'], ALPACA_CONFIG['secret_key'], True)
    sim_engine = BacktestEngine(start_date, end_date, 10000.0, client)
    sim_engine.universe = universe
    
    print("1. Fetching Historical Price Data...")
    sim_engine.load_data()
    
    # 3. Fetch Historical Macro Data (The Soros Layer)
    print("2. Fetching Historical Macro Data (VIX, SPY Trends)...")
    macro_data = yf.download(['^VIX', 'SPY'], start=start_date, end=end_date, progress=False)['Close']
    
    def get_macro_context(date_obj):
        try:
            ts = pd.Timestamp(date_obj)
            # Find nearest row
            idx = macro_data.index.get_indexer([ts], method='nearest')[0]
            row = macro_data.iloc[idx]
            
            vix = row['^VIX']
            spy_price = row['SPY']
            
            # Calculate simple trend (vs 5 days ago)
            prev_idx = max(0, idx - 5)
            prev_spy = macro_data.iloc[prev_idx]['SPY']
            
            trend = "UP" if spy_price > prev_spy else "DOWN"
            regime = "RISK_ON" if (vix < 20 and trend == "UP") else "RISK_OFF"
            
            return {'regime': regime, 'vix': round(vix, 2), 'spy_trend': trend}
            
        except Exception:
            return {'regime': 'NEUTRAL', 'vix': 20.0, 'spy_trend': 'FLAT'}

    # 4. Fetch Fundamentals (The Lynch Layer - Current Proxy)
    print("3. Fetching Fundamentals (Snapshot)...")
    fund_tool = Fundamentalist()
    fund_cache = {}
    for sym in universe:
        fund_cache[sym] = fund_tool.get_fundamentals(sym)
    
    # 5. Build Timeline & Tasks
    spy_data = sim_engine.broker.historical_data.get('SPY')
    timeline = spy_data.index[spy_data.index >= pd.Timestamp(start_date).tz_localize('UTC')]
    
    brain = AIBrain() # Prompt logic
    sem = asyncio.Semaphore(25) # Parallel limit
    tasks = []
    
    print(f"4. Generating {len(timeline)} Daily Decisions with AI (Parallel)...")
    
    # Pre-loop to build tasks
    # We need to simulate the 'state' for the prompt basics (Account Value mocked as static 10k for query, real tracking later)
    # Note: Using static 10k for prompt generation is a limitation of parallel sim, but acceptable for decision logic testing.
    mock_account = {'buying_power': 10000.0, 'portfolio_value': 10000.0}
    mock_portfolio = {} # Assuming empty start for decision purity, or we could thread state (too slow).
    # We will let the AI decide purely on Opportunity + Macro.
    
    for timestamp in timeline:
        # Context
        date_obj = timestamp.date()
        macro = get_macro_context(date_obj)
        
        # Tech Data from Sim Engine
        sim_engine.broker.update_time(timestamp)
        indicators = calculate_indicators(sim_engine.broker)
        
        # Prepare Market Data format
        market_data_dict = {}
        for sym in universe:
             ind = indicators.get(sym, {})
             market_data_dict[sym] = {
                 'price': ind.get('price', 0),
                 'rsi': ind.get('rsi', 50),
                 'vwap': 0, # Sim doesn't calc vwap yet, skip
                 'sma_200': ind.get('sma200', 0)
             }
        
        tasks.append(fetch_legendary_decision(
            date_obj, brain, mock_account, mock_portfolio, market_data_dict, macro, fund_cache, sem
        ))
        
    # Execute AI
    ai_results = await asyncio.gather(*tasks)
    decision_map = {res['date']: res for res in ai_results}
    
    print("5. Executing Trades & Generating Detailed Report...")
    
    report_lines = []
    report_lines.append("# Legendary Strategy: 1-Year Detailed Report")
    report_lines.append(f"**Period**: {start_date} -> {end_date}")
    report_lines.append("| Date | Macro | Symbol | Action | Conviction | Reasoning | Result |")
    report_lines.append("|---|---|---|---|---|---|---|")
    
    # Execution Loop
    # sim_engine.broker.reset() # Attribute Error
    
    # Re-instantiate Engine for clean execution
    exec_engine = BacktestEngine(start_date, end_date, 10000.0, client)
    exec_engine.universe = universe
    # Share loaded data to save time
    exec_engine.broker.historical_data = sim_engine.broker.historical_data
    
    for timestamp in timeline:
        date_obj = timestamp.date()
        exec_engine.broker.update_time(timestamp)
        
        # Get Decision
        day_result = decision_map.get(date_obj)
        if not day_result: continue
        
        macro = get_macro_context(date_obj)
        decisions = day_result.get('decisions', [])
        
        # Account
        account = exec_engine.broker.get_account_info()
        bp = account['portfolio_cash']
        
        for d in decisions:
            sym = d.get('symbol')
            if sym not in universe: continue
            
            action = d.get('decision')
            conviction = float(d.get('conviction', 5.0))
            reason = d.get('reasoning', '').replace('|', '-') # Escape pipes for markdown table
            
            # Execute
            trade_executed = False
            trade_details = "-"
            
            # Fix: get_current_price
            price = exec_engine.broker.get_current_price(sym)
            if not price or price <= 0: continue
            
            if action == 'buy':
                # Ruthless Sizing
                max_alloc = bp * 0.20
                alloc = max_alloc * (conviction / 10.0)
                qty = int(alloc / price)
                
                if qty > 0 and bp >= (qty * price):
                    exec_engine.broker.submit_order(sym, qty, 'buy')
                    trade_executed = True
                    trade_details = f"BOUGHT {qty} @ ${price:.2f} (${qty*price:.0f})"
                    bp -= (qty * price) # Update local BP for next trade in same day
                    
            elif action == 'sell':
                # Fix: check portfolio dict or get_portfolio_stocks
                positions = exec_engine.broker.get_portfolio_stocks()
                pos = positions.get(sym)
                
                if pos:
                    qty = pos['quantity']
                    exec_engine.broker.submit_order(sym, qty, 'sell')
                    trade_executed = True
                    trade_details = f"SOLD {qty} @ ${price:.2f}"
            
            if trade_executed:
                regime_icon = "🟢" if macro['regime'] == 'RISK_ON' else "🔴"
                report_lines.append(f"| {date_obj} | {regime_icon} {macro['regime']} | **{sym}** | {action.upper()} | {conviction} | {reason} | {trade_details} |")
                
    # Final Stats
    stats = exec_engine.get_stats()
    final_equity = stats.get('final_equity', 10000)
    total_ret = stats.get('return_pct', 0)
    
    print("\n=== SIMULATION COMPLETE ===")
    print(f"Final Equity: ${final_equity:,.2f}")
    print(f"Return: {total_ret:.2f}%")
    
    # Save Report
    with open('legendary_sim_report.md', 'w') as f:
        f.write("\n".join(report_lines))
        f.write(f"\n\n## Final Performance\n**End Balance**: ${final_equity:,.2f} (**{total_ret:.2f}%**)")
        
    print(f"Detailed report saved to: {os.path.abspath('legendary_sim_report.md')}")

if __name__ == "__main__":
    asyncio.run(run_legendary_sim())
