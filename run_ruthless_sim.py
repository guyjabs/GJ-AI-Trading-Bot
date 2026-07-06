
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import logging
import time

# Configure basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Add src to path
sys.path.append(os.getcwd())

from src.simulation_engine import SimulatorEngine

def run_detailed_sim():
    # 1. Configuration
    # FULL 1-YEAR RUN
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    initial_cash = 10000.0
    
    # Universe
    universe = ['AAPL', 'MSFT', 'SPY', 'NVDA', 'TSLA'] 
    
    print(f"=== Starting 1-Year RUTHLESS Simulation (Full Run) ===")
    print(f"Period: {start_date} to {end_date}")
    print(f"Capital: ${initial_cash:,.2f}")
    print(f"Universe: {universe}")
    print("----------------------------------")

    try:
        # 2. Initialize Engine
        sim = SimulatorEngine(start_date, end_date, initial_cash, universe)
        
        # 3. Run
        # Start timer
        t0 = time.time()
        results = sim.run()
        t1 = time.time()
        
        # 4. Report
        final_balance = results.get('final_balance', 0)
        total_return = results.get('total_return_pct', 0)
        trades_count = results.get('trades', 0)
        duration_min = (t1 - t0) / 60
        
        print("\n=== RUTHLESS SIMULATION RESULTS (1 YEAR) ===")
        print(f"Final Balance: ${final_balance:,.2f}")
        print(f"Total Return:  {total_return:.2f}%")
        print(f"Total Trades:  {trades_count}")
        print(f"Duration:      {duration_min:.1f} min")
        print("============================================")
        
        # Save equity curve for artifact
        curve = results.get('equity_curve', [])
        if curve:
            import json
            with open('simulation_results_1year_ruthless.json', 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Saved results to simulation_results_1year_ruthless.json")
            
    except Exception as e:
        print(f"Simulation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_detailed_sim()
