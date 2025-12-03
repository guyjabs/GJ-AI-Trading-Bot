"""
Research module for self-learning trading bot.
Handles news aggregation, trend analysis, and strategy research.
"""

from .news_aggregator import NewsAggregator
from .knowledge_base import KnowledgeBase
from .trend_analyzer import TrendAnalyzer
from .strategy_researcher import StrategyResearcher
from .research_scheduler import ResearchScheduler

__all__ = ['NewsAggregator', 'KnowledgeBase', 'TrendAnalyzer', 'StrategyResearcher', 'ResearchScheduler']
