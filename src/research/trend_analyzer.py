"""
Trend Analyzer and Prediction Engine.
Analyzes market trends from news and makes predictions with confidence scores.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
import statistics

from ..utils import logger
from ..api import openai
from .news_aggregator import NewsAggregator
from .knowledge_base import KnowledgeBase


class TrendAnalyzer:
    """Analyzes trends and generates predictions based on news and market data."""
    
    def __init__(self, news_aggregator: NewsAggregator, knowledge_base: KnowledgeBase):
        """
        Initialize trend analyzer.
        
        Args:
            news_aggregator: NewsAggregator instance
            knowledge_base: KnowledgeBase instance
        """
        self.news_aggregator = news_aggregator
        self.knowledge_base = knowledge_base
    
    def analyze_symbol_sentiment(self, symbol: str, hours: int = 24) -> Dict:
        """
        Analyze sentiment for a specific symbol over recent hours.
        
        Args:
            symbol: Stock or crypto symbol
            hours: Number of hours to look back
            
        Returns:
            Dictionary with sentiment analysis
        """
        # Get news for symbol
        articles = self.news_aggregator.get_news_for_symbol(symbol)
        
        # Filter by time
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_articles = []
        
        for article in articles:
            try:
                pub_date = datetime.fromisoformat(article.get('published_at', '').replace('Z', '+00:00'))
                if pub_date > cutoff:
                    recent_articles.append(article)
            except:
                continue
        
        if not recent_articles:
            return {
                'symbol': symbol,
                'article_count': 0,
                'sentiment': 0,
                'trend': 'neutral',
                'confidence': 0
            }
        
        # Calculate sentiment
        sentiment_summary = self.news_aggregator.get_sentiment_summary(recent_articles)
        
        # Determine trend
        avg_sentiment = sentiment_summary['average']
        if avg_sentiment > 0.2:
            trend = 'bullish'
        elif avg_sentiment < -0.2:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        # Confidence based on article count and sentiment consistency
        confidence = min(1.0, len(recent_articles) / 10)  # More articles = higher confidence
        
        return {
            'symbol': symbol,
            'article_count': len(recent_articles),
            'sentiment': avg_sentiment,
            'sentiment_breakdown': sentiment_summary,
            'trend': trend,
            'confidence': confidence,
            'period_hours': hours
        }
    
    def detect_emerging_trends(self, min_articles: int = 5) -> List[Dict]:
        """
        Detect emerging trends from recent news.
        
        Args:
            min_articles: Minimum number of articles to consider a trend
            
        Returns:
            List of detected trends
        """
        # Get all recent news
        articles = self.news_aggregator.fetch_all_news(use_cache=True)
        
        # Extract topics and symbols
        topic_counts = Counter()
        symbol_mentions = defaultdict(list)
        
        for article in articles:
            # Count topics
            for topic in article.get('topics', []):
                topic_counts[topic] += 1
            
            # Track symbol mentions
            for ticker in article.get('mentioned_tickers', []):
                symbol_mentions[ticker].append(article)
        
        trends = []
        
        # Identify trending topics
        for topic, count in topic_counts.most_common(10):
            if count >= min_articles:
                trends.append({
                    'type': 'topic',
                    'name': topic,
                    'article_count': count,
                    'strength': min(1.0, count / 20),
                    'detected_at': datetime.now().isoformat()
                })
        
        # Identify trending symbols
        for symbol, symbol_articles in symbol_mentions.items():
            if len(symbol_articles) >= min_articles:
                sentiment = self.news_aggregator.get_sentiment_summary(symbol_articles)
                
                trends.append({
                    'type': 'symbol',
                    'name': symbol,
                    'article_count': len(symbol_articles),
                    'sentiment': sentiment['average'],
                    'strength': min(1.0, len(symbol_articles) / 15),
                    'detected_at': datetime.now().isoformat()
                })
        
        # Store trends in knowledge base
        for trend in trends:
            trend_text = f"{trend['type'].title()} trend: {trend['name']} with {trend['article_count']} mentions"
            if 'sentiment' in trend:
                trend_text += f" (sentiment: {trend['sentiment']:.2f})"
            
            self.knowledge_base.add_trend(
                text=trend_text,
                metadata=trend
            )
        
        logger.info(f"Detected {len(trends)} emerging trends")
        return trends
    
    def generate_prediction(self, symbol: str, timeframe_days: int = 3) -> Dict:
        """
        Generate a prediction for a symbol based on news, trends, and historical patterns.
        
        Args:
            symbol: Stock or crypto symbol
            timeframe_days: Prediction timeframe in days
            
        Returns:
            Dictionary with prediction details
        """
        # Analyze recent sentiment
        sentiment_analysis = self.analyze_symbol_sentiment(symbol, hours=48)
        
        # Get recent insights from knowledge base
        insights = self.knowledge_base.get_insights_for_symbol(symbol)
        recent_insights = [i for i in insights if self._is_recent(i['metadata'].get('timestamp'), days=7)]
        
        # Get related trends
        trends = self.knowledge_base.search_trends(symbol, n_results=5)
        
        # Build context for AI prediction
        context = self._build_prediction_context(symbol, sentiment_analysis, recent_insights, trends)
        
        # Use AI to generate prediction
        prediction = self._ai_predict(symbol, context, timeframe_days)
        
        # Store prediction in knowledge base
        prediction_text = (
            f"{symbol} prediction: {prediction['direction']} movement "
            f"({prediction['expected_change']}) over {timeframe_days} days. "
            f"Confidence: {prediction['confidence']:.0%}"
        )
        
        prediction_id = self.knowledge_base.add_prediction(
            text=prediction_text,
            metadata={
                'symbol': symbol,
                'direction': prediction['direction'],
                'expected_change': prediction['expected_change'],
                'confidence': prediction['confidence'],
                'timeframe_days': timeframe_days,
                'reasoning': prediction['reasoning'],
                'sentiment': sentiment_analysis['sentiment'],
                'article_count': sentiment_analysis['article_count']
            }
        )
        
        prediction['id'] = prediction_id
        return prediction
    
    def _build_prediction_context(self, symbol: str, sentiment: Dict, insights: List[Dict], trends: List[Dict]) -> str:
        """Build context string for AI prediction."""
        context_parts = [
            f"Symbol: {symbol}",
            f"Recent Sentiment: {sentiment['trend']} (score: {sentiment['sentiment']:.2f})",
            f"News Articles (48h): {sentiment['article_count']}",
            ""
        ]
        
        if insights:
            context_parts.append("Recent Insights:")
            for insight in insights[:5]:
                context_parts.append(f"  - {insight['text']}")
            context_parts.append("")
        
        if trends:
            context_parts.append("Related Trends:")
            for trend in trends[:3]:
                context_parts.append(f"  - {trend['text']}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _ai_predict(self, symbol: str, context: str, timeframe_days: int) -> Dict:
        """Use AI to generate prediction based on context."""
        prompt = f"""Analyze the following market data and generate a price prediction.

{context}

Based on this information, predict the price movement for {symbol} over the next {timeframe_days} days.

Provide your response in JSON format:
{{
  "direction": "up|down|neutral",
  "expected_change": "percentage range (e.g., '+2-3%', '-1-2%', 'flat')",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of key factors"
}}

Consider:
- News sentiment and volume
- Recent trends and patterns
- Market context
- Be conservative with confidence scores
"""
        
        try:
            response = openai.make_ai_request(prompt)
            prediction_data = openai.parse_ai_response(response)
            
            # Validate and normalize
            if isinstance(prediction_data, list) and len(prediction_data) > 0:
                prediction_data = prediction_data[0]
            
            return {
                'direction': prediction_data.get('direction', 'neutral'),
                'expected_change': prediction_data.get('expected_change', 'unknown'),
                'confidence': float(prediction_data.get('confidence', 0.5)),
                'reasoning': prediction_data.get('reasoning', 'Insufficient data')
            }
        except Exception as e:
            logger.error(f"Error generating AI prediction: {e}")
            return {
                'direction': 'neutral',
                'expected_change': 'unknown',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}'
            }
    
    def extract_insights_from_news(self, max_articles: int = 20) -> List[Dict]:
        """
        Extract actionable insights from recent news using AI.
        
        Args:
            max_articles: Maximum number of articles to analyze
            
        Returns:
            List of extracted insights
        """
        articles = self.news_aggregator.fetch_all_news(use_cache=True)[:max_articles]
        
        if not articles:
            logger.warning("No articles to extract insights from")
            return []
        
        # Group articles by symbol/topic
        grouped = defaultdict(list)
        
        for article in articles:
            # Group by mentioned tickers
            for ticker in article.get('mentioned_tickers', []):
                grouped[ticker].append(article)
            
            # Also group by topics
            for topic in article.get('topics', []):
                grouped[f"topic:{topic}"].append(article)
        
        insights = []
        
        # Extract insights for each group
        for key, group_articles in list(grouped.items())[:10]:  # Limit to top 10 groups
            if len(group_articles) < 2:
                continue
            
            insight = self._extract_insight_from_articles(key, group_articles)
            if insight:
                insights.append(insight)
        
        logger.info(f"Extracted {len(insights)} insights from {len(articles)} articles")
        return insights
    
    def _extract_insight_from_articles(self, key: str, articles: List[Dict]) -> Optional[Dict]:
        """Extract a single insight from a group of articles."""
        # Build summary of articles
        article_summaries = []
        for article in articles[:5]:  # Limit to 5 articles per group
            summary = f"- {article.get('title', 'No title')}"
            if 'sentiment_score' in article:
                summary += f" (sentiment: {article['sentiment_score']:.2f})"
            article_summaries.append(summary)
        
        prompt = f"""Analyze these related news articles and extract a single actionable trading insight.

Topic/Symbol: {key}

Articles:
{chr(10).join(article_summaries)}

Extract ONE key insight that would be valuable for trading decisions. Be specific and actionable.

Respond with JSON:
{{
  "insight": "brief, actionable insight",
  "confidence": 0.0-1.0,
  "impact": "high|medium|low"
}}
"""
        
        try:
            response = openai.make_ai_request(prompt)
            data = openai.parse_ai_response(response)
            
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            insight_text = data.get('insight', '')
            if not insight_text:
                return None
            
            # Determine symbol
            symbol = key if not key.startswith('topic:') else None
            
            # Store in knowledge base
            metadata = {
                'source': 'ai_extraction',
                'confidence': float(data.get('confidence', 0.5)),
                'impact': data.get('impact', 'medium'),
                'article_count': len(articles)
            }
            
            if symbol:
                metadata['symbol'] = symbol
            
            insight_id = self.knowledge_base.add_insight(
                text=insight_text,
                metadata=metadata
            )
            
            return {
                'id': insight_id,
                'text': insight_text,
                'metadata': metadata
            }
        except Exception as e:
            logger.error(f"Error extracting insight for {key}: {e}")
            return None
    
    def evaluate_predictions(self, current_prices: Dict[str, float]) -> Dict:
        """
        Evaluate active predictions against current prices.
        
        Args:
            current_prices: Dictionary mapping symbols to current prices
            
        Returns:
            Dictionary with evaluation results
        """
        active_predictions = self.knowledge_base.get_active_predictions()
        
        evaluated = 0
        correct = 0
        incorrect = 0
        
        for prediction in active_predictions:
            metadata = prediction['metadata']
            symbol = metadata.get('symbol')
            
            if symbol not in current_prices:
                continue
            
            # Check if prediction timeframe has passed
            timestamp = metadata.get('timestamp', '')
            timeframe_days = metadata.get('timeframe_days', 3)
            
            try:
                pred_time = datetime.fromisoformat(timestamp)
                if datetime.now() - pred_time < timedelta(days=timeframe_days):
                    continue  # Not ready to evaluate yet
            except:
                continue
            
            # Evaluate prediction
            # (In real implementation, would compare against historical price)
            # For now, just mark as evaluated
            
            evaluated += 1
            
            # Update prediction status
            self.knowledge_base.update_prediction_outcome(
                prediction_id=prediction['id'],
                outcome='evaluated',
                actual_result={'current_price': current_prices[symbol]}
            )
        
        logger.info(f"Evaluated {evaluated} predictions")
        
        return {
            'evaluated': evaluated,
            'correct': correct,
            'incorrect': incorrect,
            'pending': len(active_predictions) - evaluated
        }
    
    def _is_recent(self, timestamp: str, days: int = 7) -> bool:
        """Check if timestamp is within recent days."""
        try:
            ts = datetime.fromisoformat(timestamp)
            return datetime.now() - ts < timedelta(days=days)
        except:
            return False
    
    def generate_market_summary(self) -> Dict:
        """
        Generate a comprehensive market summary based on recent news and trends.
        
        Returns:
            Dictionary with market summary
        """
        # Get recent news
        articles = self.news_aggregator.fetch_all_news(use_cache=True)
        
        # Get sentiment summary
        overall_sentiment = self.news_aggregator.get_sentiment_summary(articles)
        
        # Get recent trends
        trends = self.knowledge_base.get_recent_trends(limit=10)
        
        # Get active predictions
        predictions = self.knowledge_base.get_active_predictions()
        
        # Get prediction accuracy
        accuracy = self.knowledge_base.get_prediction_accuracy(days=30)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'news_count': len(articles),
            'overall_sentiment': overall_sentiment,
            'trends': trends,
            'active_predictions': len(predictions),
            'prediction_accuracy': accuracy,
            'top_symbols': self._get_top_mentioned_symbols(articles, limit=10)
        }
    
    def _get_top_mentioned_symbols(self, articles: List[Dict], limit: int = 10) -> List[Dict]:
        """Get most mentioned symbols from articles."""
        symbol_counts = Counter()
        
        for article in articles:
            for ticker in article.get('mentioned_tickers', []):
                symbol_counts[ticker] += 1
        
        return [
            {'symbol': symbol, 'mentions': count}
            for symbol, count in symbol_counts.most_common(limit)
        ]


# Test mode
if __name__ == "__main__":
    from config import NEWSAPI_KEY, ALPHAVANTAGE_API_KEY, OPENAI_API_KEY
    
    print("=== Trend Analyzer Test Mode ===\n")
    
    # Initialize components
    news_agg = NewsAggregator(
        newsapi_key=NEWSAPI_KEY if 'NEWSAPI_KEY' in dir() else None,
        alphavantage_key=ALPHAVANTAGE_API_KEY if 'ALPHAVANTAGE_API_KEY' in dir() else None
    )
    
    kb = KnowledgeBase()
    analyzer = TrendAnalyzer(news_agg, kb)
    
    # Test symbol sentiment analysis
    print("Analyzing sentiment for AAPL...")
    sentiment = analyzer.analyze_symbol_sentiment('AAPL', hours=48)
    print(f"  Trend: {sentiment['trend']}")
    print(f"  Sentiment: {sentiment['sentiment']:.2f}")
    print(f"  Articles: {sentiment['article_count']}")
    print(f"  Confidence: {sentiment['confidence']:.2f}\n")
    
    # Detect emerging trends
    print("Detecting emerging trends...")
    trends = analyzer.detect_emerging_trends(min_articles=3)
    print(f"  Found {len(trends)} trends")
    for trend in trends[:5]:
        print(f"    - {trend['type']}: {trend['name']} ({trend['article_count']} articles)")
    print()
    
    # Extract insights
    print("Extracting insights from news...")
    insights = analyzer.extract_insights_from_news(max_articles=10)
    print(f"  Extracted {len(insights)} insights")
    for insight in insights[:3]:
        print(f"    - {insight['text'][:80]}...")
    print()
    
    # Generate prediction
    print("Generating prediction for AAPL...")
    prediction = analyzer.generate_prediction('AAPL', timeframe_days=3)
    print(f"  Direction: {prediction['direction']}")
    print(f"  Expected Change: {prediction['expected_change']}")
    print(f"  Confidence: {prediction['confidence']:.0%}")
    print(f"  Reasoning: {prediction['reasoning']}\n")
    
    # Market summary
    print("Generating market summary...")
    summary = analyzer.generate_market_summary()
    print(f"  News Articles: {summary['news_count']}")
    print(f"  Overall Sentiment: {summary['overall_sentiment']['average']:.2f}")
    print(f"  Active Predictions: {summary['active_predictions']}")
    print(f"  Prediction Accuracy: {summary['prediction_accuracy']['accuracy']:.1f}%")
    print(f"\n  Top Mentioned Symbols:")
    for item in summary['top_symbols'][:5]:
        print(f"    - {item['symbol']}: {item['mentions']} mentions")
