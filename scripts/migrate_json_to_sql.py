import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.db import db, DatabaseManager

DATA_DIR = Path("data")

def migrate_performance_history():
    perf_file = DATA_DIR / "performance_history.json"
    if not perf_file.exists():
        print("No performance history found.")
        return

    print(f"Migrating {perf_file}...")
    with open(perf_file, 'r') as f:
        history = json.load(f)

    conn = db._get_connection()
    c = conn.cursor()
    
    count = 0
    for trade in history:
        # Check if already exists? (naive check)
        # Just insert history
        try:
            c.execute("""
                INSERT INTO trade_performance (
                    symbol, entry_date, entry_price, exit_date, exit_price, 
                    quantity, strategy, market_condition, profit_loss, 
                    profit_loss_pct, hold_duration_hours, is_closed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get('symbol'),
                trade.get('entry_time'),
                trade.get('entry_price'),
                trade.get('exit_time'),
                trade.get('exit_price'),
                trade.get('quantity'),
                trade.get('strategy'),
                trade.get('market_condition'),
                trade.get('profit_loss'),
                trade.get('profit_loss_pct'),
                trade.get('hold_duration_hours'),
                1 if trade.get('closed') else 0
            ))
            count += 1
        except Exception as e:
            print(f"Failed to migrate trade {trade.get('symbol')}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Migrated {count} performance records.")

def migrate_strategy_weights():
    weights_file = DATA_DIR / "strategy_weights.json"
    if not weights_file.exists():
        print("No strategy weights found.")
        return

    print(f"Migrating {weights_file}...")
    with open(weights_file, 'r') as f:
        weights = json.load(f)

    db.save_weights(weights, reason="Initial Migration")
    print("✅ Migrated strategy weights.")

def main():
    print("🚀 Starting Database Migration...")
    
    # Initialize DB (creates file)
    DatabaseManager()
    
    migrate_performance_history()
    migrate_strategy_weights()
    
    print("✨ Migration Complete!")

if __name__ == "__main__":
    main()
