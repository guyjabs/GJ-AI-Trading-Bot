"""
Trade Journal Module
Logs all trades to SQLite database for performance tracking and analysis.
"""

import sqlite3
import json
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
                    mode TEXT,
                    feature_vector TEXT,
                    exit_reason TEXT
                )
            ''')
            
            # Migrate: add new columns if they don't exist (for existing DBs)
            try:
                cursor.execute("SELECT feature_vector FROM trades LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE trades ADD COLUMN feature_vector TEXT")
                logger.info("Migrated trade journal: added feature_vector column")
            
            try:
                cursor.execute("SELECT exit_reason FROM trades LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE trades ADD COLUMN exit_reason TEXT")
                logger.info("Migrated trade journal: added exit_reason column")
            
            conn.commit()
            conn.close()
            logger.info("Trade journal database initialized")
        except Exception as e:
            logger.error(f"Error initializing trade journal: {e}")
    
    def log_entry(self, symbol: str, price: float, shares: float, strategy: str, 
                  setup_type: str = "auto", mode: str = "swing", feature_vector: dict = None):
        """Log a trade entry with optional feature vector for ML training"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            fv_json = json.dumps(feature_vector) if feature_vector else None
            
            cursor.execute('''
                INSERT INTO trades (symbol, entry_time, entry_price, shares, strategy, setup_type, mode, feature_vector)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, datetime.now().isoformat(), price, shares, strategy, setup_type, mode, fv_json))
            
            conn.commit()
            conn.close()
            logger.info(f"Logged entry for {symbol} in journal (strategy: {strategy})")
        except Exception as e:
            logger.error(f"Error logging entry: {e}")
            
    def log_exit(self, symbol: str, price: float, pnl: float, pnl_pct: float, 
                 notes: str = "", exit_reason: str = "manual"):
        """Log a trade exit (updates most recent open trade for symbol)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find most recent open trade for this specific symbol
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
                    SET exit_time = ?, exit_price = ?, pnl = ?, pnl_pct = ?, notes = ?, exit_reason = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), price, pnl, pnl_pct, notes, exit_reason, trade_id))
                
                conn.commit()
                logger.info(f"Logged exit for {symbol} in journal (PNL: ${pnl:.2f}, Reason: {exit_reason})")
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
            conn.close()
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
    
    def get_closed_trades(self):
        """Get all closed trades (with exit data) for performance analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                WHERE exit_time IS NOT NULL 
                ORDER BY exit_time DESC
            ''')
            
            trades = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return trades
        except Exception as e:
            logger.error(f"Error fetching closed trades: {e}")
            return []
    
    def get_trades_with_features(self):
        """Get closed trades that have feature vector data (for ML training)"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                WHERE exit_time IS NOT NULL 
                AND feature_vector IS NOT NULL 
                ORDER BY exit_time DESC
            ''')
            
            trades = []
            for row in cursor.fetchall():
                trade = dict(row)
                # Parse the feature vector JSON
                if trade.get('feature_vector'):
                    try:
                        trade['features'] = json.loads(trade['feature_vector'])
                    except json.JSONDecodeError:
                        trade['features'] = {}
                else:
                    trade['features'] = {}
                trade['profitable'] = (trade.get('pnl', 0) or 0) > 0
                trades.append(trade)
            
            conn.close()
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades with features: {e}")
            return []

    def get_losing_trades(self, limit=100):
        """Get recent losing trades with their feature vectors for analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                WHERE exit_time IS NOT NULL 
                AND pnl < 0 
                AND feature_vector IS NOT NULL 
                ORDER BY exit_time DESC
                LIMIT ?
            ''', (limit,))
            
            trades = []
            for row in cursor.fetchall():
                trade = dict(row)
                if trade.get('feature_vector'):
                    try:
                        trade['feature_vector'] = json.loads(trade['feature_vector'])
                    except json.JSONDecodeError:
                        trade['feature_vector'] = {}
                else:
                    trade['feature_vector'] = {}
                trades.append(trade)
                
            conn.close()
            return trades
        except Exception as e:
            logger.error(f"Error fetching losing trades: {e}")
            return []

# Global instance
trade_journal = TradeJournal()
