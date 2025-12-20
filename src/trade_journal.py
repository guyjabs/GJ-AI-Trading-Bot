"""
Trade Journal Module
Logs all trades to SQLite database for performance tracking and analysis.
"""

import sqlite3
import os
from datetime import datetime
from .utils import logger

class TradeJournal:
    """SQLite-based trade journal for performance tracking"""
    
    def __init__(self, db_path="data/trade_journal.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    entry_time TIMESTAMP,
                    exit_time TIMESTAMP,
                    entry_price REAL,
                    exit_price REAL,
                    shares REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    strategy TEXT,
                    setup_type TEXT,
                    stop_loss REAL,
                    target REAL,
                    risk_reward REAL,
                    notes TEXT,
                    emotional_state TEXT,
                    market_context TEXT,
                    mode TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Trade journal database initialized")
        except Exception as e:
            logger.error(f"Error initializing trade journal: {e}")
    
    def log_entry(self, symbol: str, price: float, shares: float, strategy: str, setup_type: str = "auto", mode: str = "swing"):
        """Log a trade entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (symbol, entry_time, entry_price, shares, strategy, setup_type, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, datetime.now(), price, shares, strategy, setup_type, mode))
            
            conn.commit()
            conn.close()
            logger.info(f"Logged entry for {symbol} in journal")
        except Exception as e:
            logger.error(f"Error logging entry: {e}")
            
    def log_exit(self, symbol: str, price: float, pnl: float, pnl_pct: float, notes: str = ""):
        """Log a trade exit (updates most recent open trade for symbol)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find most recent open trade for symbol
            cursor.execute('''
                SELECT id FROM trades 
                WHERE symbol = ? AND exit_time IS NULL 
                ORDER BY entry_time DESC LIMIT 1
            ''', (symbol,))
            
            row = cursor.fetchone()
            if row:
                trade_id = row[0]
                cursor.execute('''
                    UPDATE trades 
                    SET exit_time = ?, exit_price = ?, pnl = ?, pnl_pct = ?, notes = ?
                    WHERE id = ?
                ''', (datetime.now(), price, pnl, pnl_pct, notes, trade_id))
                
                conn.commit()
                logger.info(f"Logged exit for {symbol} in journal (PNL: ${pnl:.2f})")
            else:
                logger.warning(f"Could not find open trade for {symbol} to log exit")
                
            conn.close()
        except Exception as e:
            logger.error(f"Error logging exit: {e}")
    
    def get_recent_trades(self, limit=10):
        """Get recent trades"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades ORDER BY entry_time DESC LIMIT ?
            ''', (limit,))
            
            trades = [dict(row) for row in cursor.fetchall()]
            return trades
        except Exception as e:
            logger.error(f"Error fetching recent trades: {e}")
            return []

    def get_all_trades(self):
        """Get ALL trades from history"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades ORDER BY entry_time DESC
            ''')
            
            trades = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return trades
        except Exception as e:
            logger.error(f"Error fetching all trades: {e}")
            return []

# Global instance
trade_journal = TradeJournal()
