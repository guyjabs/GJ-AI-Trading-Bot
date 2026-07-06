"""
News Aggregator for fetching and analyzing market news from multiple sources.
Supports NewsAPI, Alpha Vantage, and other financial news APIs.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils import logger

# Cache settings
NEWS_CACHE_FILE = "data/knowledge_base/news_cache.json"
CACHE_DURATION_HOURS = 1

class NewsAggregator:
    """Aggregates news from multiple sources with caching and rate limiting."""
    
    def __init__(self, newsapi_key: str = None, alphavantage_key: str = None, finnhub_key: str = None):
        """
        Initialize news aggregator with API keys.
        
        Args:
            newsapi_key: NewsAPI.org API key
            alphavantage_key: Alpha Vantage API key
            finnhub_key: Finnhub API key (optional)
        """
        self.newsapi_key = newsapi_key
        self.alphavantage_key = alphavantage_key
        self.finnhub_key = finnhub_key
        
        # Setup requests session with retry logic
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Load cache
        self.cache = self._load_cache()
        
        # Track API usage
        self.api_calls = {'newsapi': 0, 'alphavantage': 0, 'finnhub': 0}
        
    def _load_cache(self) -> Dict:
        """Load cached news articles."""
        try:
            if os.path.exists(NEWS_CACHE_FILE):
                with open(NEWS_CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                    # Filter out old cache entries
                    cutoff = (datetime.now() - timedelta(hours=CACHE_DURATION_HOURS)).isoformat()
                    cache['articles'] = [a for a in cache.get('articles', []) if a.get('fetched_at', '') > cutoff]
                    return cache
        except Exception as e:
            logger.warning(f"Error loading news cache: {e}")
        
        return {'articles': [], 'last_updated': None}
    
    def _save_cache(self):
        """Save news cache to file."""
        try:
            os.makedirs(os.path.dirname(NEWS_CACHE_FILE), exist_ok=True)
            with open(NEWS_CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving news cache: {e}")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.cache.get('last_updated'):
            return False
        
        last_updated = datetime.fromisoformat(self.cache['last_updated'])
        return datetime.now() - last_updated < timedelta(hours=CACHE_DURATION_HOURS)
    
    def fetch_newsapi(self, query: str = "stock market OR cryptocurrency", max_results: int = 50) -> List[Dict]:
        """
        Fetch news from NewsAPI.org
        
        Args:
            query: Search query
            max_results: Maximum number of articles to return
            
        Returns:
            List of news articles
        """
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured, skipping NewsAPI")
            return []
        
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'apiKey': self.newsapi_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': min(max_results, 100),
                'from': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            self.api_calls['newsapi'] += 1
            
            data = response.json()
            articles = []
            
            for article in data.get('articles', []):
                articles.append({
                    'source': 'newsapi',
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'content': article.get('content', ''),
                    'url': article.get('url', ''),
                    'published_at': article.get('publishedAt', ''),
                    'fetched_at': datetime.now().isoformat(),
                    'source_name': article.get('source', {}).get('name', 'Unknown')
                })
            
            logger.info(f"✅ NewsAPI: Fetched {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            return []
    
    def fetch_alphavantage_news(self, tickers: List[str] = None, topics: List[str] = None, 
                                time_from: str = None, time_to: str = None) -> List[Dict]:
        """
        Fetch news from Alpha Vantage News & Sentiment API
        
        Args:
            tickers: List of stock tickers to fetch news for
            topics: List of topics (e.g., 'technology', 'finance', 'blockchain')
            time_from: Start time YYYYMMDDTHHMM
            time_to: End time YYYYMMDDTHHMM
            
        Returns:
            List of news articles
        """
        if not self.alphavantage_key:
            logger.warning("Alpha Vantage key not configured, skipping Alpha Vantage")
            return []
        
        try:
            # Default time_from to today if not provided (and not historical)
            if not time_from:
                time_from = datetime.now().strftime('%Y%m%dT0000')

            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.alphavantage_key,
                'limit': 50,
                'time_from': time_from
            }
            
            if time_to:
                params['time_to'] = time_to
            
            if tickers:
                params['tickers'] = ','.join(tickers[:10])  # Max 10 tickers
            if topics:
                params['topics'] = ','.join(topics[:5])  # Max 5 topics
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            self.api_calls['alphavantage'] += 1
            
            data = response.json()
            articles = []
            
            for item in data.get('feed', []):
                # Extract ticker mentions
                ticker_sentiment = item.get('ticker_sentiment', [])
                mentioned_tickers = [ts.get('ticker') for ts in ticker_sentiment]
                
                articles.append({
                    'source': 'alphavantage',
                    'title': item.get('title', ''),
                    'summary': item.get('summary', ''),
                    'url': item.get('url', ''),
                    'published_at': item.get('time_published', ''),
                    'fetched_at': datetime.now().isoformat(),
                    'source_name': item.get('source', 'Unknown'),
                    'sentiment_score': float(item.get('overall_sentiment_score', 0)),
                    'sentiment_label': item.get('overall_sentiment_label', 'Neutral'),
                    'mentioned_tickers': mentioned_tickers,
                    'topics': [t.get('topic') for t in item.get('topics', [])]
                })
            
            logger.info(f"✅ Alpha Vantage: Fetched {len(articles)} articles with sentiment scores")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching from Alpha Vantage: {e}")
            return []
    
    def fetch_finnhub_news(self, category: str = "general") -> List[Dict]:
        """
        Fetch news from Finnhub
        
        Args:
            category: News category (general, forex, crypto, merger)
            
        Returns:
            List of news articles
        """
        if not self.finnhub_key:
            logger.debug("Finnhub key not configured, skipping Finnhub")
            return []
        
        try:
            url = f"https://finnhub.io/api/v1/news"
            params = {
                'category': category,
                'token': self.finnhub_key
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            self.api_calls['finnhub'] += 1
            
            data = response.json()
            articles = []
            
            for item in data:
                # Filter for today only
                pub_date = datetime.fromtimestamp(item.get('datetime', 0))
                if pub_date >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                    articles.append({
                        'source': 'finnhub',
                        'title': item.get('headline', ''),
                        'summary': item.get('summary', ''),
                        'url': item.get('url', ''),
                        'published_at': pub_date.isoformat(),
                        'fetched_at': datetime.now().isoformat(),
                        'source_name': item.get('source', 'Unknown'),
                        'category': item.get('category', category),
                        'image': item.get('image', '')
                    })
            
            logger.info(f"Fetched {len(articles)} articles from Finnhub")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching from Finnhub: {e}")
            return []
            
    def fetch_social_media(self, symbol: str) -> List[Dict]:
        """
        Fetch posts from crypto blogs (e.g. Cointelegraph RSS) to gauge sentiment and hype.
        """
        clean_symbol = symbol.replace("/USD", "").replace("-USD", "")
        articles = []
        
        try:
            import xml.etree.ElementTree as ET
            
            # Fetch from popular crypto blog RSS
            url = "https://cointelegraph.com/rss"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                items = root.findall('.//item')
                
                for item in items:
                    title = item.findtext('title', '')
                    description = item.findtext('description', '')
                    
                    # Check if our symbol is mentioned in this blog post
                    if clean_symbol.upper() in title.upper() or clean_symbol.upper() in description.upper():
                        articles.append({
                            'source': 'blog',
                            'title': f"[Blog] {title}",
                            'summary': description[:500], # Truncate long descriptions
                            'url': item.findtext('link', ''),
                            'published_at': datetime.now().isoformat(), # Cointelegraph RSS dates are messy, use now
                            'fetched_at': datetime.now().isoformat(),
                            'source_name': 'Cointelegraph Blog',
                            'sentiment_score': 0.0 # Will be evaluated by GPT-4
                        })
                        
            logger.info(f"✅ Crypto Blogs: Found {len(articles)} posts mentioning {clean_symbol}")
            return articles
            
        except Exception as e:
            logger.warning(f"Error fetching crypto blogs for {symbol}: {e}")
            return []
    
    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate articles based on title similarity.
        
        Args:
            articles: List of articles
            
        Returns:
            Deduplicated list of articles
        """
        seen_titles: Set[str] = set()
        unique_articles = []
        
        for article in articles:
            # Normalize title for comparison
            title = article.get('title', '').lower().strip()
            
            # Skip if we've seen a very similar title
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)
        
        logger.info(f"Deduplicated {len(articles)} articles to {len(unique_articles)}")
        return unique_articles
    
    def filter_by_relevance(self, articles: List[Dict], keywords: List[str] = None) -> List[Dict]:
        """
        Filter articles by relevance to trading/investing.
        
        Args:
            articles: List of articles
            keywords: Optional list of keywords to filter by
            
        Returns:
            Filtered list of articles
        """
        if not keywords:
            keywords = [
                'stock', 'stocks', 'market', 'trading', 'invest', 'crypto', 'bitcoin',
                'ethereum', 'earnings', 'rally', 'sell-off', 'bull', 'bear', 'fed',
                'interest rate', 'inflation', 'recession', 'growth', 'revenue'
            ]
        
        relevant_articles = []
        
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')} {article.get('summary', '')}".lower()
            
            # Check if any keyword appears in the text
            if any(keyword.lower() in text for keyword in keywords):
                relevant_articles.append(article)
        
        logger.info(f"Filtered {len(articles)} articles to {len(relevant_articles)} relevant ones")
        return relevant_articles
    
    def fetch_all_news(self, use_cache: bool = True, force_refresh: bool = False, progress_callback=None) -> List[Dict]:
        """
        Fetch news from all configured sources.
        
        Args:
            use_cache: Whether to use cached results if available
            force_refresh: Force refresh even if cache is valid
            progress_callback: Function to emit progress events
            
        Returns:
            Combined list of news articles from all sources
        """
        # Report start
        if progress_callback:
            progress_callback("🔌 Connecting to news sources...", 10, 'detail')

        # Check cache first
        if use_cache and not force_refresh and self._is_cache_valid():
            logger.info(f"Using cached news ({len(self.cache['articles'])} articles)")
            if progress_callback:
                progress_callback(f"✅ Found {len(self.cache['articles'])} articles in local cache", 100, 'done')
            return self.cache['articles']
        
        logger.info("🔍 Starting news research cycle...")
        logger.info(f"📰 Fetching fresh news from {sum([1 for k in [self.newsapi_key, self.alphavantage_key, self.finnhub_key] if k])} configured sources")
        
        all_articles = []
        current_progress = 10
        
        # Fetch from NewsAPI
        if self.newsapi_key:
            if progress_callback:
                progress_callback("📰 Scavenging NewsAPI.org for global market news...", current_progress + 10, 'in-progress')
            
            newsapi_articles = self.fetch_newsapi()
            all_articles.extend(newsapi_articles)
            
            if progress_callback:
                progress_callback(f"✓ Found {len(newsapi_articles)} articles from NewsAPI", current_progress + 20, 'detail')
            
            time.sleep(1)  # Rate limiting
            current_progress += 20
        
        # Fetch from Alpha Vantage
        if self.alphavantage_key:
            if progress_callback:
                progress_callback("📊 Querying Alpha Vantage for sentiment data...", current_progress + 5, 'in-progress')
            
            # Fetch general market news
            av_articles = self.fetch_alphavantage_news(topics=['technology', 'finance', 'blockchain'])
            all_articles.extend(av_articles)
            
            if progress_callback:
                progress_callback(f"✓ Found {len(av_articles)} sentiment-scored articles from Alpha Vantage", current_progress + 15, 'detail')
                
            time.sleep(1)  # Rate limiting
            current_progress += 15
        
        # Fetch from Finnhub
        if self.finnhub_key:
            if progress_callback:
                progress_callback("💎 Mining Finnhub for crypto & general news...", current_progress + 5, 'in-progress')
                
            fh_articles = []
            fh_articles.extend(self.fetch_finnhub_news('general'))
            fh_articles.extend(self.fetch_finnhub_news('crypto'))
            all_articles.extend(fh_articles)
            
            if progress_callback:
                progress_callback(f"✓ Retrieved {len(fh_articles)} articles from Finnhub", current_progress + 15, 'detail')
                
            time.sleep(1)  # Rate limiting
            current_progress += 15
        
        # Deduplicate and filter
        if progress_callback:
            progress_callback(f"🧹 Cleaning and deduplicating {len(all_articles)} raw articles...", current_progress + 5, 'in-progress')
            
        all_articles = self.deduplicate_articles(all_articles)
        all_articles = self.filter_by_relevance(all_articles)
        
        # Sort by published date (newest first)
        all_articles.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        # Update cache
        self.cache = {
            'articles': all_articles,
            'last_updated': datetime.now().isoformat()
        }
        self._save_cache()
        
        logger.info(f"📊 Research Summary: {len(all_articles)} unique, relevant articles collected")
        
        if progress_callback:
            sentiment = self.get_sentiment_summary(all_articles)
            avg_sent = sentiment['average']
            sentiment_text = "Bullish 🟢" if avg_sent > 0.05 else "Bearish 🔴" if avg_sent < -0.05 else "Neutral ⚪"
            progress_callback(f"🧠 Analysis Complete: {sentiment_text} (Score: {avg_sent:.2f})", 90, 'detail')
            progress_callback(f"💾 Saved {len(all_articles)} articles to knowledge base", 100, 'done')
        
        return all_articles
    
    def get_news_for_symbol(self, symbol: str) -> List[Dict]:
        """
        Get news articles mentioning a specific symbol.
        
        Args:
            symbol: Stock or crypto symbol
            
        Returns:
            List of articles mentioning the symbol
        """
        all_articles = self.fetch_all_news(use_cache=True)
        
        symbol_articles = []
        for article in all_articles:
            # Check if symbol is mentioned in title, description, or ticker list
            text = f"{article.get('title', '')} {article.get('description', '')} {article.get('summary', '')}".upper()
            mentioned_tickers = [t.upper() for t in article.get('mentioned_tickers', [])]
            
            if symbol.upper() in text or symbol.upper() in mentioned_tickers:
                symbol_articles.append(article)
                
        # Also fetch social media directly for this symbol
        social_posts = self.fetch_social_media(symbol)
        symbol_articles.extend(social_posts)
        
        logger.info(f"Found {len(symbol_articles)} articles (including social) for {symbol}")
        return symbol_articles
    
    def get_sentiment_summary(self, articles: List[Dict]) -> Dict:
        """
        Get sentiment summary from a list of articles.
        
        Args:
            articles: List of articles
            
        Returns:
            Dictionary with sentiment statistics
        """
        if not articles:
            return {'average': 0, 'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
        
        sentiments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for article in articles:
            sentiment = article.get('sentiment_score', 0)
            sentiments.append(sentiment)
            
            if sentiment > 0.15:
                positive_count += 1
            elif sentiment < -0.15:
                negative_count += 1
            else:
                neutral_count += 1
        
        return {
            'average': sum(sentiments) / len(sentiments) if sentiments else 0,
            'positive': positive_count,
            'negative': negative_count,
            'neutral': neutral_count,
            'total': len(articles)
        }


    def get_catalyst_for_symbol(self, symbol: str, hours: int = 24) -> Dict:
        """
        Check if there is a news catalyst for a specific symbol.
        
        Args:
            symbol: Stock symbol
            hours: Lookback period in hours
            
        Returns:
            Dict with catalyst details
        """
        try:
            # Construct query
            query = f"{symbol} stock OR {symbol} earnings OR {symbol} news"
            
            # Fetch recent news (force refresh for specific symbol check)
            # We use a shorter lookback for catalyst check
            from_date = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d')
            
            articles = []
            
            # Try Finnhub first for company specific news
            if self.finnhub_key:
                # Finnhub company news implementation would go here
                # Finnhub Company News
                # Endpoint: /company-news?symbol=AAPL&from=2021-09-01&to=2021-09-09
                fh_url = "https://finnhub.io/api/v1/company-news"
                fh_params = {
                    'symbol': symbol,
                    'from': from_date,
                    'to': datetime.now().strftime('%Y-%m-%d'),
                    'token': self.finnhub_key
                }
                fh_resp = self.session.get(fh_url, params=fh_params, timeout=10)
                if fh_resp.status_code == 200:
                    fh_data = fh_resp.json()
                    # Convert to standard format
                    for item in fh_data:
                        articles.append({
                            'source': 'finnhub',
                            'title': item.get('headline', ''),
                            'description': item.get('summary', ''),
                            'url': item.get('url', ''),
                            'publishedAt': datetime.fromtimestamp(item.get('datetime', 0)).isoformat(),
                            'urlToImage': item.get('image', '')
                        })
                    logger.info(f"✅ Finnhub: Found {len(fh_data)} specific articles for {symbol}")
                
            # Fallback to NewsAPI
            if not articles and self.newsapi_key:
                url = "https://newsapi.org/v2/everything"
                params = {
                    'q': query,
                    'from': from_date,
                    'sortBy': 'relevancy',
                    'language': 'en',
                    'apiKey': self.newsapi_key
                }
                resp = self.session.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    articles = data.get('articles', [])
            
            if not articles:
                return {'has_catalyst': False, 'reason': 'No recent news found'}
                
            # Analyze top article
            top_article = articles[0]
            title = top_article.get('title', '')
            description = top_article.get('description', '')
            
            # Simple keyword check for catalyst type
            catalyst_type = 'news'
            text = (title + " " + description).lower()
            
            if 'earnings' in text or 'revenue' in text or 'eps' in text:
                catalyst_type = 'earnings'
            elif 'upgrade' in text or 'downgrade' in text or 'target' in text:
                catalyst_type = 'analyst'
            elif 'fda' in text or 'approval' in text:
                catalyst_type = 'regulatory'
            elif 'fda' in text or 'approval' in text:
                catalyst_type = 'regulatory'
            elif 'merger' in text or 'acquisition' in text:
                catalyst_type = 'merger'
            elif any(x in text for x in ['layoff', 'job cut', 'downsizing', 'reduction in force', 'letting go', 'staff reduction']):
                catalyst_type = 'layoffs'
                # Extract snippet for reasoning if possible?
                # Just return presence for now.
                
            return {
                'has_catalyst': True,
                'catalyst_type': catalyst_type,
                'headline': title,
                'url': top_article.get('url'),
                'published_at': top_article.get('publishedAt')
            }
            
        except Exception as e:
            logger.error(f"Error checking catalyst for {symbol}: {e}")
            return {'has_catalyst': False, 'error': str(e)}

    def get_news_for_date(self, target_date: datetime) -> List[Dict]:
        """
        Fetch news for a specific historical date.
        
        Args:
            target_date: Date object
            
        Returns:
            List of news articles from that day
        """
        articles = []
        date_str = target_date.strftime('%Y-%m-%d')
        next_date_str = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.info(f"📰 Fetching historical news for {date_str}...")
        
        # 1. Alpha Vantage (Primary for History)
        # Alpha Vantage supports deeper history than free NewsAPI
        if self.alphavantage_key:
            try:
                # Format: YYYYMMDDTHHMM
                time_from = target_date.strftime('%Y%m%dT0000')
                time_to = target_date.strftime('%Y%m%dT2359')
                
                av_articles = self.fetch_alphavantage_news(
                    topics=['finance', 'technology', 'economy_macro', 'financial_markets'], 
                    time_from=time_from,
                    time_to=time_to
                )
                articles.extend(av_articles)
                logger.info(f"✅ Historical News (AlphaVantage): Found {len(av_articles)} articles")
            except Exception as e:
                logger.error(f"Alpha Vantage history error: {e}")

        # 2. NewsAPI (Secondary - often limited to 1 month)
        if self.newsapi_key and len(articles) < 5:
            try:
                url = "https://newsapi.org/v2/everything"
                params = {
                    'q': 'stock market OR economy OR finance OR fed OR inflation',
                    'from': date_str,
                    'to': date_str,
                    'sortBy': 'popularity',
                    'language': 'en',
                    'apiKey': self.newsapi_key,
                    'pageSize': 20
                }
                resp = self.session.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    na_articles = []
                    for item in data.get('articles', []):
                         na_articles.append({
                            'source': 'newsapi',
                            'title': item.get('title'),
                            'description': item.get('description'),
                            'url': item.get('url'),
                            'published_at': item.get('publishedAt')
                        })
                    logger.info(f"✅ Historical News (NewsAPI): Found {len(na_articles)} articles")
                    articles.extend(na_articles)
            except Exception as e:
                logger.error(f"NewsAPI history error: {e}")
                
        # 2. Add Market Context (Synthetic Fallback)
        # If no news found (e.g. API limits), generate generic context based on date
        # In a real system we might query polygon.io or cached database
        if len(articles) < 5:
             articles.append({
                'source': 'market_context',
                'title': f'Market Overview for {date_str}',
                'description': f'Daily trading session analysis for {date_str}. Reviewing major index movements and sector performance.',
                'url': '',
                'published_at': date_str + 'T09:00:00Z'
            })
            
        return articles


# Test mode for standalone execution
if __name__ == "__main__":
    import sys
    
    # Load config
    try:
        from config import NEWSAPI_KEY, ALPHAVANTAGE_API_KEY, FINNHUB_API_KEY
    except ImportError:
        print("Error: config.py not found. Please create it from config.py.example")
        sys.exit(1)
    
    print("=== News Aggregator Test Mode ===\\n")
    
    aggregator = NewsAggregator(
        newsapi_key=NEWSAPI_KEY if 'NEWSAPI_KEY' in dir() else None,
        alphavantage_key=ALPHAVANTAGE_API_KEY if 'ALPHAVANTAGE_API_KEY' in dir() else None,
        finnhub_key=FINNHUB_API_KEY if 'FINNHUB_API_KEY' in dir() else None
    )
    
    # Fetch news
    print("Fetching news from all sources...\\n")
    articles = aggregator.fetch_all_news(force_refresh=True)
    
    print(f"\\nTotal articles fetched: {len(articles)}\\n")
    
    # Show first 5 articles
    print("=== Latest News ===\\n")
    for i, article in enumerate(articles[:5], 1):
        print(f"{i}. {article.get('title', 'No title')}")
        print(f"   Source: {article.get('source_name', 'Unknown')}")
        print(f"   Published: {article.get('published_at', 'Unknown')}")
        if 'sentiment_score' in article:
            print(f"   Sentiment: {article['sentiment_score']:.2f} ({article.get('sentiment_label', 'N/A')})")
        print(f"   URL: {article.get('url', 'N/A')}\\n")
    
    # Test symbol-specific news
    print("\\n=== News for AAPL ===\\n")
    aapl_news = aggregator.get_news_for_symbol('AAPL')
    print(f"Found {len(aapl_news)} articles mentioning AAPL\\n")
    
    for i, article in enumerate(aapl_news[:3], 1):
        print(f"{i}. {article.get('title', 'No title')}")
        print(f"   {article.get('url', 'N/A')}\\n")
    
    # Sentiment summary
    print("\\n=== Overall Sentiment ===\\n")
    sentiment = aggregator.get_sentiment_summary(articles)
    print(f"Total articles: {sentiment['total']}")
    print(f"Positive: {sentiment['positive']} ({sentiment['positive']/sentiment['total']*100:.1f}%)")
    print(f"Negative: {sentiment['negative']} ({sentiment['negative']/sentiment['total']*100:.1f}%)")
    print(f"Neutral: {sentiment['neutral']} ({sentiment['neutral']/sentiment['total']*100:.1f}%)")
    print(f"Average sentiment: {sentiment['average']:.3f}")
