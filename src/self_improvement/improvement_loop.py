import os
from datetime import datetime
from src.utils import logger
from .performance_analyzer import PerformanceAnalyzer
from .strategy_optimizer import StrategyOptimizer

class SelfImprovementLoop:
    """
    Orchestrates the performance analysis and strategy optimization loop.
    Typically run offline (e.g. weekends) to retrain models and adjust params.
    """
    REPORT_DIR = 'data/improvement_reports'

    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.optimizer = StrategyOptimizer()

    def run(self) -> dict:
        """
        Executes one full self-improvement cycle.
        """
        logger.info("Starting Self-Improvement Loop...")
        
        # 1. Analyze performance
        report = self.analyzer.analyze()
        
        if not report.get('sufficient_data'):
            msg = f"Not enough data for self-improvement yet (need 20+ closed trades, have {report.get('total_trades', 0)})"
            logger.info(msg)
            return {'status': 'insufficient_data', 'total_trades': report.get('total_trades', 0)}
            
        # 2. Optimize strategies
        changes = self.optimizer.optimize(report)
        
        # 3. Apply changes and retrain models if needed
        if changes:
            self.optimizer.apply_changes(changes)
            
            # Retrain Quant Model
            try:
                from src.signals.quant_model import QuantModel
                from src.trade_journal import trade_journal
                
                model = QuantModel()
                training_data = trade_journal.get_trades_with_features()
                if training_data:
                    logger.info(f"Attempting to retrain QuantModel with {len(training_data)} trades...")
                    model.train(training_data)
            except Exception as e:
                logger.error(f"Failed to retrain QuantModel during self-improvement: {e}")
                
        # 3.5 Run AI Code Optimizer
        try:
            from src.self_improvement.ai_optimizer import AIOptimizer
            from src.trade_journal import trade_journal
            
            ai_opt = AIOptimizer()
            losing_trades = trade_journal.get_losing_trades(limit=100)
            if losing_trades:
                ai_opt.generate_dynamic_rules(losing_trades)
        except Exception as e:
            logger.error(f"Failed to run AIOptimizer: {e}")
                
        # 4. Generate Report
        report_path = self._generate_report(report, changes)
        
        # 5. Send Notification
        self._send_notification(report, changes)
        
        logger.info(f"Self-Improvement Loop completed. {len(changes)} changes made.")
        
        return {
            'status': 'completed',
            'changes_made': len(changes),
            'report': report,
            'changes': changes,
            'report_path': report_path
        }

    def _generate_report(self, report: dict, changes: list) -> str:
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.REPORT_DIR, f"improvement_report_{timestamp}.md")
        
        try:
            with open(filepath, 'w') as f:
                f.write(f"# Self-Improvement Report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("## Performance Summary\n")
                f.write(f"- **Total Trades:** {report.get('total_trades')}\n")
                f.write(f"- **Win Rate:** {report.get('win_rate', 0):.1%}\n")
                f.write(f"- **Total PnL:** ${report.get('total_pnl', 0):.2f}\n")
                f.write(f"- **Profit Factor:** {report.get('profit_factor', 0):.2f}\n")
                f.write(f"- **Max Drawdown:** ${report.get('max_drawdown', 0):.2f}\n\n")
                
                f.write("## Strategy Breakdown\n")
                for strat, stats in report.get('strategy_breakdown', {}).items():
                    f.write(f"- **{strat}**: {stats['trades']} trades | Win Rate: {stats['win_rate']:.1%} | Avg PnL: {stats['avg_pnl_pct']:.2%}\n")
                f.write("\n")
                
                f.write("## Changes & Recommendations\n")
                if not changes:
                    f.write("*No changes recommended in this cycle.*\n")
                else:
                    for change in changes:
                        f.write(f"- **{change['parameter']}**: {change['old_value']} -> {change['new_value']} ({change['reason']})\n")
                        
            return filepath
        except Exception as e:
            logger.error(f"Failed to generate markdown report: {e}")
            return ""

    def _send_notification(self, report: dict, changes: list):
        try:
            from src.notifications import notifier
            wr = report.get('win_rate', 0) * 100
            pnl = report.get('total_pnl', 0)
            msg = f"Self-Improvement Complete: {len(changes)} changes made. Win rate: {wr:.1f}%. Total PnL: ${pnl:.2f}"
            notifier.notify_trade("SYSTEM", "IMPROVE", 0, 0, msg)
        except Exception as e:
            logger.error(f"Failed to send self-improvement notification: {e}")
