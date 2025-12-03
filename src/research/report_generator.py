"""
Report Generator - Generates research reports and summaries.
Creates daily market summaries, trend reports, and strategy insights.
"""

import json
import os
from datetime import datetime
from typing import Dict, List

from ..utils import logger
from .knowledge_base import KnowledgeBase
from .trend_analyzer import TrendAnalyzer

REPORT_DIR = "data/reports"

class ReportGenerator:
    """Generates various research reports."""
    
    def __init__(self, knowledge_base: KnowledgeBase, trend_analyzer: TrendAnalyzer):
        """
        Initialize report generator.
        
        Args:
            knowledge_base: KnowledgeBase instance
            trend_analyzer: TrendAnalyzer instance
        """
        self.knowledge_base = knowledge_base
        self.trend_analyzer = trend_analyzer
        os.makedirs(REPORT_DIR, exist_ok=True)
    
    def generate_daily_report(self) -> str:
        """
        Generate a comprehensive daily research report.
        
        Returns:
            Path to the generated report file
        """
        try:
            # Gather data
            summary = self.trend_analyzer.generate_market_summary()
            
            # Format report
            date_str = datetime.now().strftime('%Y-%m-%d')
            report_content = [
                f"# Daily Market Research Report - {date_str}",
                f"Generated at: {datetime.now().strftime('%H:%M:%S')}",
                "",
                "## Market Overview",
                f"- **Sentiment**: {summary['overall_sentiment']['average']:.2f} "
                f"({summary['overall_sentiment']['positive']} positive, {summary['overall_sentiment']['negative']} negative)",
                f"- **News Volume**: {summary['news_count']} articles analyzed",
                f"- **Active Predictions**: {summary['active_predictions']}",
                f"- **Prediction Accuracy (30d)**: {summary['prediction_accuracy']['accuracy']:.1f}%",
                "",
                "## Top Trending Symbols",
            ]
            
            for item in summary['top_symbols'][:5]:
                report_content.append(f"- **{item['symbol']}**: {item['mentions']} mentions")
            
            report_content.append("")
            report_content.append("## Emerging Trends")
            
            for trend in summary['trends'][:5]:
                report_content.append(f"### {trend['text']}")
                report_content.append(f"- Type: {trend['metadata'].get('type', 'Unknown')}")
                report_content.append(f"- Strength: {trend['metadata'].get('strength', 0):.2f}")
                report_content.append("")
            
            # Save report
            filename = f"daily_report_{date_str}.md"
            filepath = os.path.join(REPORT_DIR, filename)
            
            with open(filepath, 'w') as f:
                f.write('\n'.join(report_content))
            
            logger.info(f"Generated daily report: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return None

# Test mode
if __name__ == "__main__":
    from .news_aggregator import NewsAggregator
    
    print("=== Report Generator Test Mode ===\n")
    
    kb = KnowledgeBase()
    # Mock news aggregator for testing report generation without API calls
    class MockNewsAggregator:
        def fetch_all_news(self, **kwargs): return []
        def get_sentiment_summary(self, articles): 
            return {'average': 0.5, 'positive': 10, 'negative': 2, 'neutral': 5, 'total': 17}
            
    trend_analyzer = TrendAnalyzer(MockNewsAggregator(), kb)
    generator = ReportGenerator(kb, trend_analyzer)
    
    report_path = generator.generate_daily_report()
    print(f"Report generated at: {report_path}")
