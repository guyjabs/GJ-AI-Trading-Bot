"""
Research Scheduler - Manages automated research tasks.
Handles hourly news fetching, daily strategy research, and prediction evaluation.
"""

import time
import schedule
from datetime import datetime
from typing import Callable, Dict

from ..utils import logger
from .news_aggregator import NewsAggregator
from .knowledge_base import KnowledgeBase
from .trend_analyzer import TrendAnalyzer
from .strategy_researcher import StrategyResearcher


class ResearchScheduler:
    """Manages automated research tasks on various schedules."""
    
    def __init__(self, 
                 news_aggregator: NewsAggregator,
                 knowledge_base: KnowledgeBase,
                 trend_analyzer: TrendAnalyzer,
                 strategy_researcher: StrategyResearcher):
        """
        Initialize research scheduler.
        
        Args:
            news_aggregator: NewsAggregator instance
            knowledge_base: KnowledgeBase instance
            trend_analyzer: TrendAnalyzer instance
            strategy_researcher: StrategyResearcher instance
        """
        self.news_aggregator = news_aggregator
        self.knowledge_base = knowledge_base
        self.trend_analyzer = trend_analyzer
        self.strategy_researcher = strategy_researcher
        
        self.is_running = False
        self.last_run_times = {}
    
    def hourly_news_fetch(self):
        """Fetch and analyze news every hour."""
        try:
            logger.info("=== Hourly News Fetch Started ===")
            
            # Fetch fresh news
            articles = self.news_aggregator.fetch_all_news(force_refresh=True)
            logger.info(f"Fetched {len(articles)} news articles")
            
            # Detect emerging trends
            trends = self.trend_analyzer.detect_emerging_trends(min_articles=3)
            logger.info(f"Detected {len(trends)} emerging trends")
            
            # Extract insights from news
            insights = self.trend_analyzer.extract_insights_from_news(max_articles=20)
            logger.info(f"Extracted {len(insights)} insights")
            
            # Update last run time
            self.last_run_times['news_fetch'] = datetime.now()
            
            logger.info("=== Hourly News Fetch Complete ===")
            
            return {
                'articles': len(articles),
                'trends': len(trends),
                'insights': len(insights)
            }
            
        except Exception as e:
            logger.error(f"Error in hourly news fetch: {e}")
            return None
    
    def daily_strategy_research(self):
        """Research new trading strategies daily."""
        try:
            logger.info("=== Daily Strategy Research Started ===")
            
            # Run comprehensive research
            summary = self.strategy_researcher.run_daily_research()
            logger.info(f"Extracted {summary['total_insights']} strategy insights")
            
            # Update last run time
            self.last_run_times['strategy_research'] = datetime.now()
            
            logger.info("=== Daily Strategy Research Complete ===")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in daily strategy research: {e}")
            return None
    
    def daily_prediction_generation(self, symbols: list):
        """Generate predictions for tracked symbols daily."""
        try:
            logger.info("=== Daily Prediction Generation Started ===")
            
            predictions = []
            
            for symbol in symbols:
                try:
                    prediction = self.trend_analyzer.generate_prediction(symbol, timeframe_days=3)
                    predictions.append(prediction)
                    logger.info(f"Generated prediction for {symbol}: {prediction['direction']} ({prediction['confidence']:.0%})")
                except Exception as e:
                    logger.error(f"Error generating prediction for {symbol}: {e}")
            
            # Update last run time
            self.last_run_times['prediction_generation'] = datetime.now()
            
            logger.info(f"=== Daily Prediction Generation Complete ({len(predictions)} predictions) ===")
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error in daily prediction generation: {e}")
            return []
    
    def weekly_prediction_evaluation(self, current_prices: Dict[str, float]):
        """Evaluate predictions weekly."""
        try:
            logger.info("=== Weekly Prediction Evaluation Started ===")
            
            results = self.trend_analyzer.evaluate_predictions(current_prices)
            logger.info(f"Evaluated {results['evaluated']} predictions")
            
            # Get accuracy stats
            accuracy = self.knowledge_base.get_prediction_accuracy(days=30)
            logger.info(f"30-day prediction accuracy: {accuracy['accuracy']:.1f}%")
            
            # Update last run time
            self.last_run_times['prediction_evaluation'] = datetime.now()
            
            logger.info("=== Weekly Prediction Evaluation Complete ===")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in weekly prediction evaluation: {e}")
            return None
    
    def daily_knowledge_export(self):
        """Export knowledge base to JSON daily for backup."""
        try:
            logger.info("=== Daily Knowledge Export Started ===")
            
            self.knowledge_base.export_to_json()
            
            stats = self.knowledge_base.get_stats()
            logger.info(f"Exported knowledge base: {stats}")
            
            # Update last run time
            self.last_run_times['knowledge_export'] = datetime.now()
            
            logger.info("=== Daily Knowledge Export Complete ===")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in daily knowledge export: {e}")
            return None
    
    def setup_schedules(self, 
                       news_interval_hours: int = 1,
                       strategy_research_time: str = "02:00",
                       prediction_time: str = "08:00",
                       evaluation_day: str = "sunday",
                       export_time: str = "23:00"):
        """
        Setup automated schedules.
        
        Args:
            news_interval_hours: Hours between news fetches
            strategy_research_time: Time for daily strategy research (HH:MM)
            prediction_time: Time for daily prediction generation (HH:MM)
            evaluation_day: Day for weekly prediction evaluation
            export_time: Time for daily knowledge export (HH:MM)
        """
        # Clear existing schedules
        schedule.clear()
        
        # Hourly news fetch
        schedule.every(news_interval_hours).hours.do(self.hourly_news_fetch)
        logger.info(f"Scheduled: News fetch every {news_interval_hours} hour(s)")
        
        # Daily strategy research
        schedule.every().day.at(strategy_research_time).do(self.daily_strategy_research)
        logger.info(f"Scheduled: Strategy research daily at {strategy_research_time}")
        
        # Daily prediction generation (requires symbols to be passed)
        # This will be called manually from main loop with current symbols
        schedule.every().day.at(prediction_time).do(
            lambda: logger.info("Prediction generation scheduled (run manually with symbols)")
        )
        logger.info(f"Scheduled: Prediction generation daily at {prediction_time}")
        
        # Weekly prediction evaluation
        getattr(schedule.every(), evaluation_day.lower()).at("10:00").do(
            lambda: logger.info("Prediction evaluation scheduled (run manually with prices)")
        )
        logger.info(f"Scheduled: Prediction evaluation every {evaluation_day} at 10:00")
        
        # Daily knowledge export
        schedule.every().day.at(export_time).do(self.daily_knowledge_export)
        logger.info(f"Scheduled: Knowledge export daily at {export_time}")
    
    def run_pending(self):
        """Run pending scheduled tasks."""
        schedule.run_pending()
    
    def start(self, blocking: bool = False):
        """
        Start the scheduler.
        
        Args:
            blocking: If True, run in blocking mode (infinite loop)
        """
        self.is_running = True
        logger.info("Research scheduler started")
        
        if blocking:
            while self.is_running:
                self.run_pending()
                time.sleep(60)  # Check every minute
        else:
            # Non-blocking mode - caller should call run_pending() periodically
            pass
    
    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        logger.info("Research scheduler stopped")
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            'is_running': self.is_running,
            'last_run_times': self.last_run_times,
            'pending_jobs': len(schedule.jobs),
            'next_run': str(schedule.next_run()) if schedule.jobs else None
        }


# Test mode
if __name__ == "__main__":
    from config import NEWSAPI_KEY, ALPHAVANTAGE_API_KEY
    
    print("=== Research Scheduler Test Mode ===\n")
    
    # Initialize components
    news_agg = NewsAggregator(
        newsapi_key=NEWSAPI_KEY if 'NEWSAPI_KEY' in dir() else None,
        alphavantage_key=ALPHAVANTAGE_API_KEY if 'ALPHAVANTAGE_API_KEY' in dir() else None
    )
    
    kb = KnowledgeBase()
    analyzer = TrendAnalyzer(news_agg, kb)
    researcher = StrategyResearcher(kb)
    
    scheduler = ResearchScheduler(news_agg, kb, analyzer, researcher)
    
    # Setup schedules (for testing, use short intervals)
    print("Setting up schedules...")
    scheduler.setup_schedules(
        news_interval_hours=1,
        strategy_research_time="02:00",
        prediction_time="08:00"
    )
    
    # Show status
    status = scheduler.get_status()
    print(f"\nScheduler Status:")
    print(f"  Running: {status['is_running']}")
    print(f"  Pending Jobs: {status['pending_jobs']}")
    print(f"  Next Run: {status['next_run']}\n")
    
    # Run tasks manually for testing
    print("Running hourly news fetch (test)...")
    result = scheduler.hourly_news_fetch()
    if result:
        print(f"  Articles: {result['articles']}")
        print(f"  Trends: {result['trends']}")
        print(f"  Insights: {result['insights']}\n")
    
    print("Running daily strategy research (test)...")
    summary = scheduler.daily_strategy_research()
    if summary:
        print(f"  Total Insights: {summary['total_insights']}\n")
    
    print("Running daily knowledge export (test)...")
    stats = scheduler.daily_knowledge_export()
    if stats:
        print(f"  Insights: {stats.get('insights_count', 0)}")
        print(f"  Trends: {stats.get('trends_count', 0)}")
        print(f"  Predictions: {stats.get('predictions_count', 0)}\n")
    
    print("Test complete!")
