"""
Machine Learning Engine for self-learning trading bot.
Tracks performance, learns patterns, and adjusts strategy weights.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
# Removed sklearn.linear_model.LinearRegression as it's no longer used.

from .utils import logger
from .data.db import db

# ML Dependencies
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pandas as pd

# Removed file constants; everything is in DB now.
MIN_TRADES_FOR_LEARNING = 10  # Minimum trades before adjusting weights

class MLEngine:
    def __init__(self):
        # We don't cache performance_history in memory anymore to ensure fresh data
        # We still cache weights for quick access, but they are single-source-of-truth in DB.
        self.strategy_weights = self.load_strategy_weights()
        self.model = None
        self.is_trained = False
        self.encoder = LabelEncoder()
        
        # Try to train on startup
        try:
            self.train_model()
        except Exception as e:
            logger.warning(f"Could not train ML model on startup: {e}")
    
    def load_strategy_weights(self):
        """Load strategy weights from DB"""
        weights = db.load_latest_weights()
        if not weights:
            # Defaults
            logger.info("No weights in DB, using defaults.")
            weights = {
                'momentum': 0.30,
                'growth': 0.40,
                'value': 0.30
            }
            db.save_weights(weights, reason="Initial Defaults")
        else:
            logger.info(f"Loaded strategy weights: {weights}")
        return weights
    
    def save_strategy_weights(self):
        """Save strategy weights to DB"""
        db.save_weights(self.strategy_weights, reason="ML Update")
    
    def record_trade(self, symbol: str, decision: str, quantity: float, 
                     entry_price: float, strategy: str, market_condition: str = "normal", 
                     features: dict = None):
        """Record a trade entry for future learning."""
        entry_data = {
            'symbol': symbol,
            'entry_price': entry_price,
            'quantity': quantity,
            'strategy': strategy,
            'market_condition': market_condition,
            'features': features or {}
        }
        db.record_entry(entry_data)
        logger.info(f"Recorded {decision} trade for {symbol} via {strategy} strategy (DB)")
    
    def close_trade(self, symbol: str, exit_price: float):
        """Close an open trade and calculate performance."""
        result = db.record_exit(symbol, exit_price)
        if result:
            pl = result['profit_loss']
            pl_pct = result['profit_loss_pct']
            logger.info(f"Closed trade for {symbol}: P&L ${pl:.2f} ({pl_pct:.2f}%)")
            
            # Trigger learning if we have enough data?
            # Creating a lightweight check to avoid heavy DB queries on every close
            # Or just run it every time, assuming volume isn't massive.
            # Efficient way: Check total closed trades count
            # For now, let's just trigger it. SQLite is fast.
            self.learn_and_adjust()
            return result
        else:
            return None
    
    def calculate_strategy_performance(self, days: int = 30) -> Dict[str, Dict]:
        """
        Calculate performance metrics for each strategy over the last N days.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        history = db.get_performance_history() # returns list of dicts (sqlite3.Row objects behave like dicts)
        
        # Filter in memory for now (or move filtering to SQL query for efficiency)
        recent_trades = [
            t for t in history 
            if t['is_closed'] and datetime.fromisoformat(t['exit_date']) > cutoff_date
        ]
        
        if not recent_trades:
            return {}
        
        strategies = {}
        for strategy in ['momentum', 'growth', 'value']:
            strategy_trades = [t for t in recent_trades if t['strategy'] == strategy]
            
            if not strategy_trades:
                strategies[strategy] = {
                    'num_trades': 0,
                    'win_rate': 0,
                    'avg_profit_loss_pct': 0,
                    'total_profit_loss': 0,
                    'avg_hold_hours': 0
                }
                continue
            
            # Convert row objects to verify access
            wins = [t for t in strategy_trades if t['profit_loss'] > 0]
            
            strategies[strategy] = {
                'num_trades': len(strategy_trades),
                'win_rate': len(wins) / len(strategy_trades) if strategy_trades else 0,
                'avg_profit_loss_pct': np.mean([t['profit_loss_pct'] for t in strategy_trades]),
                'total_profit_loss': sum([t['profit_loss'] for t in strategy_trades]),
                'avg_hold_hours': np.mean([t['hold_duration_hours'] for t in strategy_trades])
            }
        
        return strategies

    # --- Phase 5: Granular ML ---
    def train_model(self):
        """Train Random Forest on historical trade performance."""
        logger.info("Training Granular ML Model...")
        
        history = db.get_performance_history()
        if len(history) < 20: # Need decent sample size
            logger.info("Not enough data to train ML model (need 20+ trades).")
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(history)
        
        # Features & Target
        # Target: Did the trade make money? (1 or 0)
        df['target'] = (df['profit_loss'] > 0).astype(int)
        
        # Features to use
        features = ['entry_price', 'feature_rsi', 'feature_volatility', 'feature_sentiment']
        # Handle 'spy_trend' text feature if exists
        if 'feature_spy_trend' in df.columns:
             # Simple encoding: Bullish=1, Bearish=0
             df['spy_trend_enc'] = df['feature_spy_trend'].apply(lambda x: 1 if x == 'bullish' else 0)
             features.append('spy_trend_enc')
        
        # Drop rows with missing features
        df_clean = df.dropna(subset=features)
        
        if len(df_clean) < 10:
             logger.info("Not enough clean data for training.")
             return
             
        X = df_clean[features]
        y = df_clean['target']
        
        # Train
        self.model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        self.model.fit(X, y)
        self.is_trained = True
        logger.info(f"✅ Random Forest Model Trained on {len(df_clean)} trades.")

    def predict_trade_confidence(self, current_features: dict) -> float:
        """
        Predict probability of success for a potential trade.
        Returns float between 0.0 and 1.0
        """
        if not self.is_trained or not self.model:
            return 0.5 # Neutral confidence
            
        try:
            # Prepare input vector matching training features
            # ['entry_price', 'feature_rsi', 'feature_volatility', 'feature_sentiment', 'spy_trend_enc']
            
            spy_val = 1 if current_features.get('spy_trend') == 'bullish' else 0
            
            input_vector = pd.DataFrame([{
                'entry_price': current_features.get('price', 0),
                'feature_rsi': current_features.get('rsi', 50),
                'feature_volatility': current_features.get('volatility', 0),
                'feature_sentiment': current_features.get('sentiment', 0),
                'spy_trend_enc': spy_val
            }])
            
            # Predict probability of class 1 (Profit)
            prob = self.model.predict_proba(input_vector)[0][1]
            return float(prob)
        except Exception as e:
            logger.error(f"Prediction Error: {e}")
            return 0.5
    
    def learn_and_adjust(self):
        """
        Analyze performance and adjust strategy weights using machine learning.
        """
        logger.info("Running ML learning cycle (DB-based)...")
        
        # Get performance over last 30 days
        performance = self.calculate_strategy_performance(days=30)
        
        if not performance or all(p['num_trades'] == 0 for p in performance.values()):
            logger.info("Not enough data for learning yet")
            return
        
        # Log and Calculate
        scores = {}
        for strategy, metrics in performance.items():
            logger.info(f"{strategy.capitalize()} - Trades: {metrics['num_trades']}, Win Rate: {metrics['win_rate']:.1%}")
            
            if metrics['num_trades'] > 0:
                normalized_pl = (metrics['avg_profit_loss_pct'] + 10) / 20
                normalized_pl = max(0, min(1, normalized_pl))
                scores[strategy] = (metrics['win_rate'] * 0.4) + (normalized_pl * 0.6)
            else:
                scores[strategy] = 0.33

        # Normalize logic same as before...
        total_score = sum(scores.values())
        if total_score > 0:
            new_weights = {k: v / total_score for k, v in scores.items()}
            
            # Smoothing (70/30)
            smoothed_weights = {}
            for strategy in ['momentum', 'growth', 'value']:
                old_weight = self.strategy_weights.get(strategy, 0.33)
                new_weight = new_weights.get(strategy, 0.33)
                smoothed_weights[strategy] = (new_weight * 0.7) + (old_weight * 0.3)
            
            total = sum(smoothed_weights.values())
            self.strategy_weights = {k: v / total for k, v in smoothed_weights.items()}
            
            self.save_strategy_weights()
            logger.info(f"Adjusted strategy weights: {self.strategy_weights}")
            return self.strategy_weights
            
        return self.strategy_weights

    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get overall performance summary (for UI)"""
        performance = self.calculate_strategy_performance(days)
        
        # Recalculate totals
        total_trades = sum(p['num_trades'] for p in performance.values())
        total_pl = sum(p['total_profit_loss'] for p in performance.values())
        
        weighted_win_rate = 0
        if total_trades > 0:
            weighted_win_rate = sum(
                p['win_rate'] * p['num_trades'] for p in performance.values()
            ) / total_trades
        
        return {
            'total_trades': total_trades,
            'overall_win_rate': weighted_win_rate,
            'total_profit_loss': total_pl,
            'strategies': performance,
            'current_weights': self.strategy_weights,
            'period_days': days
        }

# Global instance
ml_engine = MLEngine()
