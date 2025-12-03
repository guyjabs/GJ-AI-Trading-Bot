"""
Machine Learning Engine for self-learning trading bot.
Tracks performance, learns patterns, and adjusts strategy weights.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
from sklearn.linear_model import LinearRegression

from .utils import logger

PERFORMANCE_FILE = "data/performance_history.json"
MIN_TRADES_FOR_LEARNING = 10  # Minimum trades before adjusting weights

class MLEngine:
    def __init__(self):
        self.performance_history = self.load_performance_history()
        self.strategy_weights = {
            'momentum': 0.30,
            'growth': 0.40,
            'value': 0.30
        }
        self.load_strategy_weights()
    
    def load_performance_history(self) -> List[Dict]:
        """Load trade performance history from file"""
        if os.path.exists(PERFORMANCE_FILE):
            try:
                with open(PERFORMANCE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading performance history: {e}")
        return []
    
    def save_performance_history(self):
        """Save performance history to file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open(PERFORMANCE_FILE, 'w') as f:
                json.dump(self.performance_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving performance history: {e}")
    
    def load_strategy_weights(self):
        """Load strategy weights from file"""
        weights_file = "data/strategy_weights.json"
        if os.path.exists(weights_file):
            try:
                with open(weights_file, 'r') as f:
                    self.strategy_weights = json.load(f)
                logger.info(f"Loaded strategy weights: {self.strategy_weights}")
            except Exception as e:
                logger.error(f"Error loading strategy weights: {e}")
    
    def save_strategy_weights(self):
        """Save strategy weights to file"""
        weights_file = "data/strategy_weights.json"
        try:
            os.makedirs("data", exist_ok=True)
            with open(weights_file, 'w') as f:
                json.dump(self.strategy_weights, f, indent=2)
            logger.info(f"Saved strategy weights: {self.strategy_weights}")
        except Exception as e:
            logger.error(f"Error saving strategy weights: {e}")
    
    def record_trade(self, symbol: str, decision: str, quantity: float, 
                     entry_price: float, strategy: str, market_condition: str = "normal"):
        """
        Record a trade for future learning.
        
        Args:
            symbol: Stock symbol
            decision: 'buy' or 'sell'
            quantity: Number of shares
            entry_price: Price at entry
            strategy: Which strategy selected this stock ('momentum', 'growth', 'value')
            market_condition: Market state ('bull', 'bear', 'normal', 'volatile')
        """
        trade_record = {
            'symbol': symbol,
            'decision': decision,
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.now().isoformat(),
            'strategy': strategy,
            'market_condition': market_condition,
            'exit_price': None,
            'exit_time': None,
            'profit_loss': None,
            'profit_loss_pct': None,
            'hold_duration_hours': None,
            'closed': False
        }
        
        self.performance_history.append(trade_record)
        self.save_performance_history()
        logger.info(f"Recorded {decision} trade for {symbol} via {strategy} strategy")
    
    def close_trade(self, symbol: str, exit_price: float):
        """
        Close an open trade and calculate performance.
        
        Args:
            symbol: Stock symbol
            exit_price: Price at exit
        """
        # Find the most recent open trade for this symbol
        for trade in reversed(self.performance_history):
            if trade['symbol'] == symbol and not trade['closed']:
                trade['exit_price'] = exit_price
                trade['exit_time'] = datetime.now().isoformat()
                trade['closed'] = True
                
                # Calculate P&L
                if trade['decision'] == 'buy':
                    # We bought, now selling
                    pl = (exit_price - trade['entry_price']) * trade['quantity']
                    pl_pct = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
                else:
                    # We sold (short), now buying back
                    pl = (trade['entry_price'] - exit_price) * trade['quantity']
                    pl_pct = ((trade['entry_price'] - exit_price) / trade['entry_price']) * 100
                
                trade['profit_loss'] = pl
                trade['profit_loss_pct'] = pl_pct
                
                # Calculate hold duration
                entry_time = datetime.fromisoformat(trade['entry_time'])
                exit_time = datetime.fromisoformat(trade['exit_time'])
                duration = (exit_time - entry_time).total_seconds() / 3600  # hours
                trade['hold_duration_hours'] = duration
                
                self.save_performance_history()
                logger.info(f"Closed trade for {symbol}: P&L ${pl:.2f} ({pl_pct:.2f}%)")
                
                # Trigger learning if we have enough data
                if len([t for t in self.performance_history if t['closed']]) >= MIN_TRADES_FOR_LEARNING:
                    self.learn_and_adjust()
                
                return trade
        
        logger.warning(f"No open trade found for {symbol}")
        return None
    
    def calculate_strategy_performance(self, days: int = 30) -> Dict[str, Dict]:
        """
        Calculate performance metrics for each strategy over the last N days.
        
        Returns:
            Dict with strategy names as keys and performance metrics as values
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_trades = [
            t for t in self.performance_history 
            if t['closed'] and datetime.fromisoformat(t['exit_time']) > cutoff_date
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
            
            wins = [t for t in strategy_trades if t['profit_loss'] > 0]
            losses = [t for t in strategy_trades if t['profit_loss'] <= 0]
            
            strategies[strategy] = {
                'num_trades': len(strategy_trades),
                'win_rate': len(wins) / len(strategy_trades) if strategy_trades else 0,
                'avg_profit_loss_pct': np.mean([t['profit_loss_pct'] for t in strategy_trades]),
                'total_profit_loss': sum([t['profit_loss'] for t in strategy_trades]),
                'avg_hold_hours': np.mean([t['hold_duration_hours'] for t in strategy_trades]),
                'best_trade': max([t['profit_loss_pct'] for t in strategy_trades]),
                'worst_trade': min([t['profit_loss_pct'] for t in strategy_trades])
            }
        
        return strategies
    
    def learn_and_adjust(self):
        """
        Analyze performance and adjust strategy weights using machine learning.
        Uses recent performance to optimize allocation.
        """
        logger.info("Running ML learning cycle...")
        
        # Get performance over last 30 days
        performance = self.calculate_strategy_performance(days=30)
        
        if not performance or all(p['num_trades'] == 0 for p in performance.values()):
            logger.info("Not enough data for learning yet")
            return
        
        # Log current performance
        for strategy, metrics in performance.items():
            logger.info(f"{strategy.capitalize()} - Trades: {metrics['num_trades']}, "
                       f"Win Rate: {metrics['win_rate']:.1%}, "
                       f"Avg P&L: {metrics['avg_profit_loss_pct']:.2f}%")
        
        # Calculate new weights based on performance
        # Weight by: (win_rate * 0.4) + (avg_profit_loss_pct * 0.6)
        scores = {}
        for strategy, metrics in performance.items():
            if metrics['num_trades'] > 0:
                # Normalize avg P&L to 0-1 range (assuming -10% to +10% range)
                normalized_pl = (metrics['avg_profit_loss_pct'] + 10) / 20
                normalized_pl = max(0, min(1, normalized_pl))  # Clamp to 0-1
                
                # Combined score
                scores[strategy] = (metrics['win_rate'] * 0.4) + (normalized_pl * 0.6)
            else:
                scores[strategy] = 0.33  # Default if no trades
        
        # Normalize scores to sum to 1.0
        total_score = sum(scores.values())
        if total_score > 0:
            new_weights = {k: v / total_score for k, v in scores.items()}
            
            # Apply smoothing: 70% new weights + 30% old weights (avoid drastic changes)
            smoothed_weights = {}
            for strategy in ['momentum', 'growth', 'value']:
                old_weight = self.strategy_weights.get(strategy, 0.33)
                new_weight = new_weights.get(strategy, 0.33)
                smoothed_weights[strategy] = (new_weight * 0.7) + (old_weight * 0.3)
            
            # Normalize again
            total = sum(smoothed_weights.values())
            self.strategy_weights = {k: v / total for k, v in smoothed_weights.items()}
            
            # Save new weights
            self.save_strategy_weights()
            
            logger.info(f"Adjusted strategy weights: {self.strategy_weights}")
            logger.info(f"Changes: Momentum {(self.strategy_weights['momentum'] - old_weight)*100:+.1f}%, "
                       f"Growth {(self.strategy_weights['growth'] - performance.get('growth', {}).get('win_rate', 0.33))*100:+.1f}%, "
                       f"Value {(self.strategy_weights['value'] - performance.get('value', {}).get('win_rate', 0.33))*100:+.1f}%")
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get overall performance summary"""
        performance = self.calculate_strategy_performance(days)
        
        # Calculate overall metrics
        all_trades = []
        for strategy_perf in performance.values():
            if strategy_perf['num_trades'] > 0:
                all_trades.extend([strategy_perf])
        
        if not all_trades:
            return {
                'total_trades': 0,
                'overall_win_rate': 0,
                'total_profit_loss': 0,
                'strategies': performance,
                'current_weights': self.strategy_weights
            }
        
        total_trades = sum(p['num_trades'] for p in performance.values())
        total_pl = sum(p['total_profit_loss'] for p in performance.values())
        
        # Weighted win rate
        weighted_win_rate = sum(
            p['win_rate'] * p['num_trades'] 
            for p in performance.values() if p['num_trades'] > 0
        ) / total_trades if total_trades > 0 else 0
        
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
