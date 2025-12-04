"""
Research module for self-learning trading bot.
Handles news aggregation, trend analysis, knowledge management, and automated research.
"""

from .news_aggregator import NewsAggregator
from .knowledge_base import KnowledgeBase
from .trend_analyzer import TrendAnalyzer
from .strategy_researcher import StrategyResearcher
from .research_scheduler import ResearchScheduler
from .research_archiver import ResearchArchiver

# Import config to initialize instances
try:
    from config import NEWSAPI_KEY, ALPHAVANTAGE_API_KEY, FINNHUB_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
except ImportError:
    # Handle case where config might not be available (e.g. during tests)
    NEWSAPI_KEY = None
    ALPHAVANTAGE_API_KEY = None
    FINNHUB_API_KEY = None
    REDDIT_CLIENT_ID = None
    REDDIT_CLIENT_SECRET = None

# Initialize Singleton Instances
# This allows other modules (like day_screener) to import 'news_agg' directly
kb = KnowledgeBase()
news_agg = NewsAggregator(
    newsapi_key=NEWSAPI_KEY,
    alphavantage_key=ALPHAVANTAGE_API_KEY,
    finnhub_key=FINNHUB_API_KEY
)
trend_analyzer = TrendAnalyzer(news_agg, kb)
strategy_researcher = StrategyResearcher(
    kb, 
    reddit_client_id=REDDIT_CLIENT_ID,
    reddit_client_secret=REDDIT_CLIENT_SECRET
)
research_scheduler = ResearchScheduler(news_agg, kb, trend_analyzer, strategy_researcher)

__all__ = [
    'NewsAggregator', 'KnowledgeBase', 'TrendAnalyzer', 'StrategyResearcher', 'ResearchScheduler', 'ResearchArchiver',
    'news_agg', 'kb', 'trend_analyzer', 'strategy_researcher', 'research_scheduler'
]
