import numpy as np
import pandas as pd
from src.utils import logger
from src.trade_journal import trade_journal

class PerformanceAnalyzer:
    """
    Analyzes historical trade data to identify strengths, weaknesses, and correlations.
    """
    def __init__(self):
        pass

    def analyze(self, min_trades: int = 20) -> dict:
        """
        Analyze all closed trades. Requires a minimum number of trades to produce a report.
        """
        trades = trade_journal.get_closed_trades()
        total_trades = len(trades)
        
        if total_trades < min_trades:
            logger.info(f"Not enough closed trades for performance analysis ({total_trades}/{min_trades}).")
            return {'sufficient_data': False, 'total_trades': total_trades}
            
        df = pd.DataFrame(trades)
        
        # Ensure correct types and handle missing
        df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0)
        df['pnl_pct'] = pd.to_numeric(df['pnl_pct'], errors='coerce').fillna(0)
        
        winners = df[df['pnl'] > 0]
        losers = df[df['pnl'] <= 0]
        
        win_rate = len(winners) / total_trades if total_trades > 0 else 0
        total_pnl = df['pnl'].sum()
        avg_pnl_pct = df['pnl_pct'].mean()
        
        gross_profit = winners['pnl'].sum()
        gross_loss = abs(losers['pnl'].sum())
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else 999.0
        
        best_trade = df.loc[df['pnl_pct'].idxmax()] if not df.empty else None
        worst_trade = df.loc[df['pnl_pct'].idxmin()] if not df.empty else None
        
        best_trade_dict = {'symbol': best_trade['symbol'], 'pnl_pct': best_trade['pnl_pct']} if best_trade is not None else {}
        worst_trade_dict = {'symbol': worst_trade['symbol'], 'pnl_pct': worst_trade['pnl_pct']} if worst_trade is not None else {}
        
        # Strategy Breakdown
        strategy_breakdown = {}
        for strategy, group in df.groupby('strategy'):
            strat_trades = len(group)
            strat_winners = len(group[group['pnl'] > 0])
            strategy_breakdown[strategy] = {
                'trades': strat_trades,
                'win_rate': strat_winners / strat_trades if strat_trades > 0 else 0,
                'avg_pnl_pct': float(group['pnl_pct'].mean()),
                'total_pnl': float(group['pnl'].sum())
            }
            
        # Exit Reason Breakdown
        exit_reason_breakdown = {}
        if 'exit_reason' in df.columns:
            for reason, group in df.groupby('exit_reason'):
                if pd.isna(reason) or not reason:
                    continue
                exit_reason_breakdown[reason] = {
                    'count': len(group),
                    'avg_pnl_pct': float(group['pnl_pct'].mean())
                }
                
        # Equity Curve and Max Drawdown
        df = df.sort_values('exit_time')
        equity_curve = df['pnl'].cumsum().tolist()
        
        max_drawdown_pct = 0.0
        if not df.empty:
            cummax = df['pnl'].cumsum().cummax()
            drawdown = cummax - df['pnl'].cumsum()
            # Approximation of drawdown percent relative to initial capital + peak (simplification)
            # More accurate requires tracking actual account balance.
            max_drawdown = float(drawdown.max())
            max_drawdown_pct = max_drawdown # Keeping as absolute dollar amount for now since we don't know total BP

        # Feature Correlations (if feature_vector is parsed)
        feature_correlations = {}
        # In a real scenario we'd parse JSON and correlate. We'll skip for this skeleton 
        # unless specifically requested, to save parsing overhead.

        report = {
            'sufficient_data': True,
            'total_trades': total_trades,
            'win_rate': float(win_rate),
            'avg_pnl_pct': float(avg_pnl_pct),
            'total_pnl': float(total_pnl),
            'best_trade': best_trade_dict,
            'worst_trade': worst_trade_dict,
            'avg_win_pct': float(winners['pnl_pct'].mean()) if not winners.empty else 0.0,
            'avg_loss_pct': float(losers['pnl_pct'].mean()) if not losers.empty else 0.0,
            'profit_factor': float(profit_factor),
            'strategy_breakdown': strategy_breakdown,
            'exit_reason_breakdown': exit_reason_breakdown,
            'equity_curve': equity_curve,
            'max_drawdown': max_drawdown_pct,
            'feature_correlations': feature_correlations
        }
        
        return report
