
import json
import os
from typing import List, Dict, Any
from src.utils import logger
from src.data.intraday_data import intraday_data

USER_CONFIG_FILE = 'data/user_config.json'

class AlertManager:
    """
    Manages user watchlist and custom alerts.
    Persists data to data/user_config.json.
    """
    def __init__(self):
        self.watchlist = []
        self.alerts = []
        self.load_config()

    def load_config(self):
        """Load watchlist and alerts from JSON file"""
        if os.path.exists(USER_CONFIG_FILE):
            try:
                with open(USER_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.watchlist = data.get('watchlist', [])
                    self.alerts = data.get('alerts', [])
                logger.info(f"Loaded {len(self.watchlist)} watchlist items and {len(self.alerts)} alerts")
            except Exception as e:
                logger.error(f"Error loading user config: {e}")
                self.watchlist = []
                self.alerts = []
        else:
            logger.info("No user config found, creating default")
            self.watchlist = ["AAPL", "TSLA", "NVDA", "AMD"]
            self.alerts = []
            self.save_config()

    def save_config(self):
        """Save current state to JSON file"""
        try:
            with open(USER_CONFIG_FILE, 'w') as f:
                json.dump({
                    'watchlist': self.watchlist,
                    'alerts': self.alerts
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving user config: {e}")

    def get_watchlist(self) -> List[str]:
        return self.watchlist

    def add_to_watchlist(self, symbol: str) -> bool:
        symbol = symbol.upper()
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            self.save_config()
            logger.info(f"Added {symbol} to watchlist")
            return True
        return False

    def remove_from_watchlist(self, symbol: str) -> bool:
        symbol = symbol.upper()
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            self.save_config()
            logger.info(f"Removed {symbol} from watchlist")
            return True
        return False

    def get_alerts(self) -> List[Dict]:
        return self.alerts

    def create_alert(self, symbol: str, condition: str, value: float) -> Dict:
        """
        Create a new alert.
        Condition: 'price_above', 'price_below', 'pct_up', 'pct_down'
        """
        alert_id = 1
        if self.alerts:
            alert_id = max(a['id'] for a in self.alerts) + 1
            
        alert = {
            'id': alert_id,
            'symbol': symbol.upper(),
            'condition': condition,
            'value': float(value),
            'triggered': False
        }
        self.alerts.append(alert)
        self.save_config()
        logger.info(f"Created alert: {alert}")
        return alert

    def delete_alert(self, alert_id: int) -> bool:
        initial_len = len(self.alerts)
        self.alerts = [a for a in self.alerts if a['id'] != alert_id]
        if len(self.alerts) < initial_len:
            self.save_config()
            logger.info(f"Deleted alert {alert_id}")
            return True
        return False

    def check_alerts(self) -> List[Dict]:
        """
        Check all active alerts against current market data.
        Returns list of triggered alerts this cycle.
        """
        triggered = []
        
        # Get unique symbols from alerts
        symbols = list(set(a['symbol'] for a in self.alerts if not a.get('triggered', False)))
        if not symbols:
            return []

        # Fetch data for symbols
        # We need efficient fetching. Some alerts need 1d history (price), others need 200d (SMA).
        # Strategy: Fetch what's needed for max requirement per symbol, or just fetch ample history.
        # Fetching 200d of 1d bars is cheap.
        
        market_data = {}
        
        for sym in symbols:
            # Check what kind of alerts exist for this symbol to optimize fetch?
            # For simplicity, fetch daily bars for last year to cover SMA200 and RSI
            try:
                # Get daily data for indicators
                df_daily = intraday_data.get_intraday_data(sym, interval="1d", period="1y")
                
                # Get intraday/current price
                # We can use the last close of daily if market is closed, or fetch current quote
                # For now using daily close which is "current" enough for 1-min latency unless strictly realtime
                # But for day trading, we might want minute bars.
                # Let's fetch minute bars for Price checks, Daily for Indicators.
                
                # Actually, alpaca wrapper returns latest available.
                current_price = 0.0
                if not df_daily.empty:
                    current_price = df_daily['Close'].iloc[-1]
                    
                market_data[sym] = {
                    'df': df_daily,
                    'price': current_price
                }
            except Exception as e:
                logger.error(f"Error fetching alert data for {sym}: {e}")

        for alert in self.alerts:
            if alert.get('triggered', False):
                continue

            sym = alert['symbol']
            if sym not in market_data or market_data[sym]['df'].empty:
                continue

            data = market_data[sym]
            df = data['df']
            price = data['price']
            
            condition = alert['condition']
            target = alert['value']
            is_hit = False
            current_value = price # Default for logging

            try:
                # --- Price Conditions ---
                if condition == 'price_above':
                    if price > target: is_hit = True
                    
                elif condition == 'price_below':
                    if price < target: is_hit = True
                    
                elif condition == 'pct_change_up':
                    # Up X% today
                    if len(df) >= 2:
                        prev_close = df['Close'].iloc[-2]
                        pc = ((price - prev_close) / prev_close) * 100
                        current_value = pc
                        if pc >= target: is_hit = True
                        
                elif condition == 'pct_change_down':
                    # Down X% today (target should be positive, e.g. 5 for 5% drop)
                    if len(df) >= 2:
                        prev_close = df['Close'].iloc[-2]
                        pc = ((price - prev_close) / prev_close) * 100
                        current_value = pc
                        if pc <= -target: is_hit = True

                # --- Indicator Conditions ---
                elif condition == 'rsi_above':
                    rsi = intraday_data.calculate_rsi(df['Close'])
                    current_value = rsi
                    if rsi > target: is_hit = True
                    
                elif condition == 'rsi_below':
                    rsi = intraday_data.calculate_rsi(df['Close'])
                    current_value = rsi
                    if rsi < target: is_hit = True
                    
                elif condition == 'volume_spike':
                    # Current Vol > Target * Avg Vol (e.g. 2.0 * Avg)
                    # Use last 20 days avg
                    if len(df) > 20:
                        avg_vol = df['Volume'].iloc[-21:-1].mean() # Exclude today for avg
                        curr_vol = df['Volume'].iloc[-1]
                        ratio = curr_vol / avg_vol if avg_vol > 0 else 0
                        current_value = ratio
                        if ratio >= target: is_hit = True
                        
                elif condition == 'price_above_sma200':
                    sma200 = intraday_data.calculate_sma(df['Close'], 200)
                    current_value = sma200
                    if sma200 > 0 and price > sma200: is_hit = True
                    
                elif condition == 'price_below_sma200':
                    sma200 = intraday_data.calculate_sma(df['Close'], 200)
                    current_value = sma200
                    if sma200 > 0 and price < sma200: is_hit = True
                    
                elif condition == 'golden_cross':
                    # SMA50 crosses above SMA200
                    # Check current relation
                    sma50 = intraday_data.calculate_sma(df['Close'], 50)
                    sma200 = intraday_data.calculate_sma(df['Close'], 200)
                    current_value = f"{sma50:.2f}/{sma200:.2f}"
                    if sma50 > 0 and sma200 > 0 and sma50 > sma200: is_hit = True
                    
            except Exception as e:
                logger.error(f"Error checking alert condition {condition} for {sym}: {e}")

            if is_hit:
                alert['triggered'] = True
                triggered.append({
                    'alert': alert,
                    'current_value': current_value,
                    'price': price
                })
                logger.info(f"🔔 ALERT TRIGGERED: {sym} {condition} Target:{target} Actual:{current_value}")

        if triggered:
            self.save_config() # Save triggered state

        return triggered

# Global instance
alert_manager = AlertManager()
