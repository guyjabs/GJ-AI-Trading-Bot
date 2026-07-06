import os
import json
from src.utils import logger
from src.config_manager import config_manager

class StrategyOptimizer:
    """
    Adjusts config parameters and strategy weights based on performance reports.
    """
    MAX_ADJUSTMENT_PCT = 0.20
    MIN_TRADES_PER_STRATEGY = 30
    OPTIMIZATION_LOG_PATH = 'data/optimization_log.json'

    def __init__(self):
        self.changes = []

    def optimize(self, performance_report: dict) -> list:
        if not performance_report.get('sufficient_data'):
            return []
            
        self.changes = []
        
        # 1. Strategy Weights
        strategy_breakdown = performance_report.get('strategy_breakdown', {})
        for strategy_name, stats in strategy_breakdown.items():
            if stats['trades'] >= self.MIN_TRADES_PER_STRATEGY:
                win_rate = stats['win_rate']
                current_weight = 1.0 # placeholder, would pull from DB/config ideally
                
                new_weight = current_weight
                if win_rate > 0.55:
                    new_weight = current_weight * (1.0 + (win_rate - 0.5) * 0.5)
                elif win_rate < 0.35:
                    new_weight = current_weight * 0.8
                
                # Cap adjustment
                max_allowed = current_weight * (1.0 + self.MAX_ADJUSTMENT_PCT)
                min_allowed = current_weight * (1.0 - self.MAX_ADJUSTMENT_PCT)
                new_weight = max(min_allowed, min(max_allowed, new_weight))
                
                if new_weight != current_weight:
                    self.changes.append({
                        'parameter': f'strategy_weight_{strategy_name}',
                        'old_value': current_weight,
                        'new_value': new_weight,
                        'reason': f"Win rate is {win_rate:.1%}"
                    })

                # 3. Disable underperforming
                if stats['trades'] > 50 and win_rate < 0.30:
                    self.changes.append({
                        'parameter': f'disable_strategy_{strategy_name}',
                        'old_value': 'enabled',
                        'new_value': 'disabled',
                        'reason': f"Win rate critically low: {win_rate:.1%} after {stats['trades']} trades"
                    })

        # 2. Position Sizing
        pf = performance_report.get('profit_factor', 1.0)
        if pf > 1.5:
            self.changes.append({
                'parameter': 'position_size_multiplier',
                'old_value': 1.0,
                'new_value': 1.10,
                'reason': f"Strong overall profit factor: {pf:.2f}"
            })
        elif pf < 0.8:
            self.changes.append({
                'parameter': 'position_size_multiplier',
                'old_value': 1.0,
                'new_value': 0.85,
                'reason': f"Weak overall profit factor: {pf:.2f}"
            })

        # 4. Exit Reasons
        exit_reasons = performance_report.get('exit_reason_breakdown', {})
        stop_loss_stats = exit_reasons.get('stop_loss')
        if stop_loss_stats and stop_loss_stats['avg_pnl_pct'] < -0.08:
            self.changes.append({
                'parameter': 'suggest_tighter_stops',
                'old_value': False,
                'new_value': True,
                'reason': f"Stop losses averaging {stop_loss_stats['avg_pnl_pct']:.1%} loss. Consider tightening."
            })

        self._save_log()
        return self.changes

    def _save_log(self):
        if not self.changes:
            return
            
        try:
            os.makedirs(os.path.dirname(self.OPTIMIZATION_LOG_PATH), exist_ok=True)
            log_data = []
            if os.path.exists(self.OPTIMIZATION_LOG_PATH):
                with open(self.OPTIMIZATION_LOG_PATH, 'r') as f:
                    log_data = json.load(f)
                    
            import datetime
            log_data.append({
                'timestamp': datetime.datetime.now().isoformat(),
                'changes': self.changes
            })
            
            with open(self.OPTIMIZATION_LOG_PATH, 'w') as f:
                json.dump(log_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving optimization log: {e}")

    def apply_changes(self, changes: list):
        """Apply changes to config manager."""
        for change in changes:
            param = change['parameter']
            val = change['new_value']
            # We skip 'suggest_' params as they are just recommendations for the report
            if not param.startswith('suggest_'):
                config_manager.set(param, val)
                logger.info(f"Applied self-improvement change: {param} -> {val}")

    def rollback_last(self):
        """Rollback last batch of changes if performance degraded."""
        try:
            if not os.path.exists(self.OPTIMIZATION_LOG_PATH):
                return
                
            with open(self.OPTIMIZATION_LOG_PATH, 'r') as f:
                log_data = json.load(f)
                
            if not log_data:
                return
                
            last_batch = log_data.pop()
            
            for change in last_batch.get('changes', []):
                param = change['parameter']
                old_val = change['old_value']
                if not param.startswith('suggest_'):
                    config_manager.set(param, old_val)
                    logger.info(f"Rolled back {param} to {old_val}")
                    
            with open(self.OPTIMIZATION_LOG_PATH, 'w') as f:
                json.dump(log_data, f, indent=4)
                
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
