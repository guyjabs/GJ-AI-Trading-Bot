"""
Test script to demonstrate research bot with detailed logging.
Run this to see the research bot in action!
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.research import NewsAggregator, KnowledgeBase, TrendAnalyzer, ResearchScheduler, ResearchArchiver
from src.utils import logger
from src.utils import logger
import config

def main():
    print("=" * 60)
    print("🤖 RESEARCH BOT DEMO - Live Research & Archiving")
    print("=" * 60)
    print()
    
    # Initialize components
    logger.info("🚀 Initializing research bot components...")
    
    news_agg = NewsAggregator(
        newsapi_key=getattr(config, 'NEWSAPI_KEY', None),
        alphavantage_key=getattr(config, 'ALPHAVANTAGE_API_KEY', None),
        finnhub_key=getattr(config, 'FINNHUB_API_KEY', None)
    )
    
    kb = KnowledgeBase()
    analyzer = TrendAnalyzer(news_agg, kb)
    archiver = ResearchArchiver()
    
    logger.info("✅ All components initialized")
    print()
    
    # Run hourly news research
    print("-" * 60)
    print("📰 RUNNING HOURLY NEWS RESEARCH CYCLE")
    print("-" * 60)
    print()
    
    logger.info("🔍 === Hourly News Research Started ===")
    
    # Fetch news
    logger.info("📡 Fetching latest market news...")
    articles = news_agg.fetch_all_news(force_refresh=True)
    logger.info(f"✅ Collected {len(articles)} news articles")
    
    # Archive news
    archiver.save_news_snapshot(articles)
    
    # Analyze sentiment
    sentiment = news_agg.get_sentiment_summary(articles)
    logger.info(f"📊 Sentiment Analysis: {sentiment['positive']} positive, {sentiment['negative']} negative, {sentiment['neutral']} neutral")
    logger.info(f"📈 Average sentiment score: {sentiment['average']:.3f}")
    
    # Detect trends
    logger.info("🔎 Analyzing news for emerging trends...")
    trends = analyzer.detect_emerging_trends(min_articles=3)
    logger.info(f"📊 Detected {len(trends)} emerging market trends")
    
    # Archive trends
    if trends:
        archiver.save_trends(trends)
        print()
        print("🔥 TOP EMERGING TRENDS:")
        for i, trend in enumerate(trends[:5], 1):
            print(f"  {i}. {trend.get('text', 'N/A')[:80]}...")
    
    # Extract insights
    logger.info("🧠 Extracting trading insights from articles...")
    insights = analyzer.extract_insights_from_news(max_articles=10)
    logger.info(f"💡 Extracted {len(insights)} actionable insights")
    
    if insights:
        print()
        print("💡 KEY INSIGHTS:")
        for i, insight in enumerate(insights[:3], 1):
            print(f"  {i}. {insight.get('text', 'N/A')[:80]}...")
    
    logger.info("✅ === Hourly News Research Complete ===")
    
    # Generate predictions
    print()
    print("-" * 60)
    print("🔮 GENERATING AI PREDICTIONS")
    print("-" * 60)
    print()
    
    test_symbols = ['AAPL', 'TSLA', 'NVDA']
    logger.info(f"🔮 === Daily Prediction Generation Started ===")
    logger.info(f"📈 Generating predictions for {len(test_symbols)} symbols...")
    
    predictions = []
    for symbol in test_symbols:
        try:
            logger.info(f"🎯 Analyzing {symbol}...")
            prediction = analyzer.generate_prediction(symbol, timeframe_days=3)
            predictions.append(prediction)
            logger.info(f"✅ {symbol}: {prediction['direction']} (Confidence: {prediction['confidence']:.0%})")
        except Exception as e:
            logger.error(f"❌ Error generating prediction for {symbol}: {e}")
    
    # Archive predictions
    if predictions:
        archiver.save_predictions(predictions)
    
    logger.info(f"✅ === Generated {len(predictions)} Predictions ===")
    
    # Show archive location
    print()
    print("=" * 60)
    print("📁 RESEARCH DATA ARCHIVED")
    print("=" * 60)
    print(f"Location: data/research_archive/{archiver.get_today_path().split('/')[-1]}/")
    print()
    print("Files saved:")
    print("  📰 news_*.json - News articles with sentiment")
    print("  📊 trends_*.json - Detected market trends")
    print("  🔮 predictions_*.json - AI predictions")
    print()
    print("✅ All research data saved for historical analysis!")
    print()

if __name__ == "__main__":
    main()
