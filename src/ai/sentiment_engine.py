import time
import json
from datetime import datetime
from src.utils import logger
from config import OPENAI_MODEL_NAME
from src.api.openai import make_ai_request, parse_ai_response

class SentimentEngine:
    """
    Analyzes news sentiment using GPT-4.
    """
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 7200  # 2 hours

    def get_sentiment(self, symbol: str) -> dict:
        """
        Fetch news and analyze sentiment. Uses cache to save API calls.
        """
        now = time.time()
        if symbol in self._cache:
            cache_entry = self._cache[symbol]
            if now - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['data']

        default_sentiment = {
            'sentiment_score': 0.0,
            'confidence': 0.0,
            'key_catalysts': [],
            'risk_factors': [],
            'news_volume': 0
        }

        # Try to fetch news
        try:
            from src.research import news_agg
            try:
                if news_agg:
                    articles = news_agg.get_news_for_symbol(symbol)
                else:
                    articles = []
            except Exception as e:
                logger.error(f"Error fetching news for {symbol}: {e}")
                articles = []
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            articles = []

        if not articles:
            return default_sentiment

        # Cap at 15 articles to save tokens
        recent_articles = articles[:15]
        
        formatted_news = ""
        for i, a in enumerate(recent_articles):
            formatted_news += f"[{i+1}] Title: {a.get('title')}\nSource: {a.get('source')}\nDate: {a.get('published_at')}\nDescription: {a.get('description')}\n\n"

        prompt = f"""You are a financial news and social sentiment analyst. Analyze these recent news articles and forum/Reddit posts about {symbol} and assess the overall market sentiment and "hype" level.

Sources (News & Forums):
{formatted_news}

Return ONLY a JSON object (no markdown, no explanation):
{{
  "sentiment_score": <float from -1.0 (extremely bearish) to 1.0 (extremely bullish). Factor in retail hype from forums heavily for cryptos>,
  "confidence": <float from 0.0 to 1.0 indicating how confident you are>,
  "key_catalysts": ["list of positive catalysts or viral trends mentioned"],
  "risk_factors": ["list of negative risks or concerns"]
}}"""

        try:
            resp = make_ai_request(prompt, model=OPENAI_MODEL_NAME)
            sentiment_data = parse_ai_response(resp)
            
            # Validate types
            score = float(sentiment_data.get('sentiment_score', 0.0))
            score = max(-1.0, min(1.0, score))
            
            conf = float(sentiment_data.get('confidence', 0.0))
            conf = max(0.0, min(1.0, conf))
            
            result = {
                'sentiment_score': score,
                'confidence': conf,
                'key_catalysts': list(sentiment_data.get('key_catalysts', [])),
                'risk_factors': list(sentiment_data.get('risk_factors', [])),
                'news_volume': len(articles)
            }
            
            self._cache[symbol] = {
                'data': result,
                'timestamp': now
            }
            return result

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return default_sentiment

    def get_sentiment_batch(self, symbols: list) -> dict:
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_sentiment(symbol)
        return results

    def clear_cache(self):
        self._cache.clear()
