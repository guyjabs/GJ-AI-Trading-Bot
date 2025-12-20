import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("data/trading_bot.db")

class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = self._get_connection()
        c = conn.cursor()

        # 1. Trades History
        # Stores all executed trades
        c.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                decision TEXT NOT NULL, -- 'buy' or 'sell'
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                strategy TEXT,         -- 'momentum', 'growth', etc.
                reasoning TEXT,
                order_id TEXT,         -- ID from broker
                status TEXT,           -- 'filled', 'pending', 'cancelled'
                asset_type TEXT DEFAULT 'STOCK', -- 'STOCK' or 'CRYPTO'
                bot_name TEXT          -- For multi-bot tracking
            )
        """)

        # 2. Performance Tracking (For ML)
        # Pairs buy/sells to track P&L
        c.execute("""
            CREATE TABLE IF NOT EXISTS trade_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_date DATETIME NOT NULL,
                exit_date DATETIME,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                strategy TEXT,
                market_condition TEXT,
                profit_loss REAL,
                profit_loss_pct REAL,
                hold_duration_hours REAL,
                is_closed BOOLEAN DEFAULT 0
            )
        """)

        # 3. Strategy Weights (The "Brain" State)
        c.execute("""
            CREATE TABLE IF NOT EXISTS strategy_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                weights_json TEXT NOT NULL, -- Stored as JSON string
                reason TEXT
            )
        """)

        # 4. Screening Results (Cache)
        c.execute("""
            CREATE TABLE IF NOT EXISTS screening_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                results_json TEXT NOT NULL
            )
        """)
        
        # 5. Schema Upgrade (Phase 5)
        # Check if new columns exist, if not add them
        try:
            c.execute("SELECT feature_rsi FROM trade_performance LIMIT 1")
        except sqlite3.OperationalError:
            # Columns don't exist, add them
            logger.info("Upgrading DB schema for Phase 5 ML features...")
            c.execute("ALTER TABLE trade_performance ADD COLUMN feature_rsi REAL")
            c.execute("ALTER TABLE trade_performance ADD COLUMN feature_volatility REAL")
            c.execute("ALTER TABLE trade_performance ADD COLUMN feature_sentiment REAL")
            c.execute("ALTER TABLE trade_performance ADD COLUMN feature_spy_trend TEXT")

        conn.commit()
        conn.close()

    # --- Trade Logging ---
    def log_trade(self, trade_data: dict):
        """
        Log a raw trade execution.
        trade_data: {symbol, decision, quantity, price, strategy, reasoning, ...}
        """
        conn = self._get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO trades (symbol, decision, quantity, price, timestamp, strategy, reasoning, asset_type, bot_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data['symbol'],
                trade_data['decision'],
                trade_data['quantity'],
                trade_data['price'],
                trade_data.get('timestamp', datetime.now().isoformat()),
                trade_data.get('strategy', 'unknown'),
                trade_data.get('reasoning', ''),
                trade_data.get('asset_type', 'STOCK'),
                trade_data.get('bot_name', 'Global')
            ))
            conn.commit()
            return c.lastrowid
        except Exception as e:
            logger.error(f"DB Error logging trade: {e}")
        finally:
            conn.close()

    # --- Performance Tracking (ML) ---
    def record_entry(self, entry_data: dict):
        """Record an entry for performance tracking."""
        conn = self._get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO trade_performance (
                    symbol, entry_date, entry_price, quantity, strategy, market_condition,
                    feature_rsi, feature_volatility, feature_sentiment, feature_spy_trend, is_closed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                entry_data['symbol'],
                entry_data.get('timestamp', datetime.now().isoformat()),
                entry_data['entry_price'],
                entry_data['quantity'],
                entry_data.get('strategy', 'unknown'),
                entry_data.get('market_condition', 'normal'),
                entry_data.get('features', {}).get('rsi'),
                entry_data.get('features', {}).get('volatility'),
                entry_data.get('features', {}).get('sentiment'),
                entry_data.get('features', {}).get('spy_trend')
            ))
            conn.commit()
        finally:
            conn.close()

    def record_exit(self, symbol: str, exit_price: float, exit_time=None):
        """Close the most recent open trade for a symbol."""
        conn = self._get_connection()
        c = conn.cursor()
        try:
            # Find open trade
            c.execute("""
                SELECT id, entry_price, quantity, entry_date 
                FROM trade_performance 
                WHERE symbol = ? AND is_closed = 0 
                ORDER BY entry_date DESC LIMIT 1
            """, (symbol,))
            row = c.fetchone()
            
            if not row:
                logger.warning(f"No open trade found to close for {symbol}")
                return None

            trade_id, entry_price, quantity, entry_date_str = row
            exit_time = exit_time or datetime.now().isoformat()
            
            # Calcs
            pl = (exit_price - entry_price) * quantity
            pl_pct = ((exit_price - entry_price) / entry_price) * 100
            
            entry_dt = datetime.fromisoformat(entry_date_str)
            exit_dt = datetime.fromisoformat(exit_time) if isinstance(exit_time, str) else exit_time
            duration = (exit_dt - entry_dt).total_seconds() / 3600

            c.execute("""
                UPDATE trade_performance 
                SET exit_date = ?, exit_price = ?, profit_loss = ?, profit_loss_pct = ?, hold_duration_hours = ?, is_closed = 1
                WHERE id = ?
            """, (exit_time, exit_price, pl, pl_pct, duration, trade_id))
            conn.commit()
            
            return {'profit_loss': pl, 'profit_loss_pct': pl_pct}
        finally:
            conn.close()

    def get_performance_history(self):
        """Retrieve full performance history."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM trade_performance ORDER BY entry_date DESC")
            return [dict(row) for row in c.fetchall()]
        finally:
            conn.close()

    # --- Strategy Weights ---
    def save_weights(self, weights: dict, reason: str = "update"):
        conn = self._get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO strategy_weights (weights_json, reason) VALUES (?, ?)", 
                      (json.dumps(weights), reason))
            conn.commit()
        finally:
            conn.close()

    def load_latest_weights(self):
        conn = self._get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT weights_json FROM strategy_weights ORDER BY timestamp DESC LIMIT 1")
            row = c.fetchone()
            if row:
                return json.loads(row[0])
            return None
        finally:
            conn.close()

    # --- Screening Cache ---
    def save_screening_cache(self, results: dict):
        """Save screening results to cache."""
        conn = self._get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO screening_cache (results_json) VALUES (?)", 
                      (json.dumps(results),))
            conn.commit()
        finally:
            conn.close()

    def load_screening_cache(self):
        """Load latest screening results."""
        conn = self._get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT results_json FROM screening_cache ORDER BY timestamp DESC LIMIT 1")
            row = c.fetchone()
            if row:
                return json.loads(row[0])
            return {'all': []}
        finally:
            conn.close()

# Global Instance
db = DatabaseManager()
