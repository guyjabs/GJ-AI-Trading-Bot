"""
Strategy Researcher - Automatically researches new trading strategies from various sources.
Scrapes trading blogs, forums, and analyzes popular strategies.
"""

import re
import time
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

from ..utils import logger
from ..api import openai
from .knowledge_base import KnowledgeBase


class StrategyResearcher:
    """Researches and analyzes trading strategies from online sources."""
    
    def __init__(self, knowledge_base: KnowledgeBase, reddit_client_id: str = None, reddit_client_secret: str = None):
        """
        Initialize strategy researcher.
        
        Args:
            knowledge_base: KnowledgeBase instance
            reddit_client_id: Optional Reddit API client ID
            reddit_client_secret: Optional Reddit API client secret
        """
        self.knowledge_base = knowledge_base
        self.reddit_client_id = reddit_client_id
        self.reddit_client_secret = reddit_client_secret
        
        # Setup requests session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def research_investopedia_strategies(self) -> List[Dict]:
        """
        Scrape trading strategy articles from Investopedia.
        
        Returns:
            List of strategy insights
        """
        strategies = []
        
        # List of Investopedia strategy articles
        urls = [
            'https://www.investopedia.com/articles/active-trading/101014/basics-algorithmic-trading-concepts-and-examples.asp',
            'https://www.investopedia.com/articles/trading/09/short-term-trading.asp',
            'https://www.investopedia.com/articles/trading/06/daytradingretail.asp'
        ]
        
        for url in urls:
            try:
                logger.info(f"Scraping {url}")
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract title
                title = soup.find('h1')
                title_text = title.get_text(strip=True) if title else 'Unknown'
                
                # Extract main content
                article_body = soup.find('div', {'id': 'article-body_1-0'})
                if not article_body:
                    article_body = soup.find('article')
                
                if article_body:
                    paragraphs = article_body.find_all('p')
                    content = ' '.join([p.get_text(strip=True) for p in paragraphs[:10]])
                    
                    # Extract insights using AI
                    insight = self._extract_strategy_insight(title_text, content, url)
                    if insight:
                        strategies.append(insight)
                
                time.sleep(2)  # Be respectful with scraping
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
        
        logger.info(f"Extracted {len(strategies)} strategies from Investopedia")
        return strategies
    
    def research_reddit_strategies(self, subreddits: List[str] = None, limit: int = 10) -> List[Dict]:
        """
        Research trading strategies from Reddit (requires PRAW).
        
        Args:
            subreddits: List of subreddit names
            limit: Number of posts to analyze per subreddit
            
        Returns:
            List of strategy insights
        """
        if not self.reddit_client_id or not self.reddit_client_secret:
            logger.warning("Reddit API credentials not configured, skipping Reddit research")
            return []
        
        if not subreddits:
            subreddits = ['stocks', 'investing', 'algotrading']
        
        strategies = []
        
        try:
            import praw
            
            reddit = praw.Reddit(
                client_id=self.reddit_client_id,
                client_secret=self.reddit_client_secret,
                user_agent='TradingBot/1.0'
            )
            
            for subreddit_name in subreddits:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # Get top posts from the week
                    for post in subreddit.top('week', limit=limit):
                        # Filter for strategy-related posts
                        if any(keyword in post.title.lower() for keyword in ['strategy', 'trading', 'indicator', 'pattern', 'signal']):
                            
                            content = f"{post.title}\n\n{post.selftext[:500]}"
                            
                            # Extract insights
                            insight = self._extract_strategy_insight(
                                post.title,
                                content,
                                f"https://reddit.com{post.permalink}"
                            )
                            
                            if insight:
                                insight['metadata']['source'] = f'reddit_{subreddit_name}'
                                insight['metadata']['score'] = post.score
                                strategies.append(insight)
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error researching r/{subreddit_name}: {e}")
            
            logger.info(f"Extracted {len(strategies)} strategies from Reddit")
            
        except ImportError:
            logger.warning("PRAW not installed, skipping Reddit research. Install with: pip install praw")
        except Exception as e:
            logger.error(f"Error with Reddit API: {e}")
        
        return strategies
    
    def _extract_strategy_insight(self, title: str, content: str, source_url: str) -> Optional[Dict]:
        """
        Extract actionable trading insights from strategy content using AI.
        
        Args:
            title: Article/post title
            content: Article/post content
            source_url: Source URL
            
        Returns:
            Dictionary with insight or None
        """
        prompt = f"""Analyze this trading strategy article and extract actionable insights.

Title: {title}

Content: {content[:1000]}

Extract:
1. Key strategy concepts
2. Practical application for algorithmic trading
3. Risk considerations
4. Viability assessment

Respond with JSON:
{{
  "strategy_name": "brief name",
  "key_concepts": ["concept1", "concept2"],
  "application": "how to apply in algo trading",
  "risks": "key risks to consider",
  "viability": "high|medium|low",
  "reasoning": "why this strategy is/isn't viable"
}}

If the content doesn't contain useful trading strategy information, return {{"viability": "none"}}.
"""
        
        try:
            response = openai.make_ai_request(prompt)
            data = openai.parse_ai_response(response)
            
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            # Skip if not viable
            if data.get('viability') == 'none':
                return None
            
            # Create insight text
            insight_text = f"Strategy: {data.get('strategy_name', 'Unknown')} - {data.get('application', 'No application')}"
            
            # Store in knowledge base
            metadata = {
                'type': 'strategy',
                'source': 'web_research',
                'source_url': source_url,
                'strategy_name': data.get('strategy_name', 'Unknown'),
                'key_concepts': ','.join(data.get('key_concepts', [])),
                'viability': data.get('viability', 'unknown'),
                'risks': data.get('risks', ''),
                'timestamp': datetime.now().isoformat()
            }
            
            insight_id = self.knowledge_base.add_insight(
                text=insight_text,
                metadata=metadata
            )
            
            return {
                'id': insight_id,
                'text': insight_text,
                'metadata': metadata,
                'full_data': data
            }
            
        except Exception as e:
            logger.error(f"Error extracting strategy insight: {e}")
            return None
    
    def research_technical_indicators(self) -> List[Dict]:
        """
        Research and document common technical indicators.
        
        Returns:
            List of indicator insights
        """
        indicators = [
            {
                'name': 'RSI (Relative Strength Index)',
                'description': 'Momentum oscillator measuring speed and magnitude of price changes',
                'application': 'Identify overbought (>70) and oversold (<30) conditions',
                'viability': 'high'
            },
            {
                'name': 'MACD (Moving Average Convergence Divergence)',
                'description': 'Trend-following momentum indicator showing relationship between two moving averages',
                'application': 'Signal line crossovers indicate buy/sell opportunities',
                'viability': 'high'
            },
            {
                'name': 'Bollinger Bands',
                'description': 'Volatility bands placed above and below moving average',
                'application': 'Price touching upper band suggests overbought, lower band suggests oversold',
                'viability': 'medium'
            },
            {
                'name': 'Volume Weighted Average Price (VWAP)',
                'description': 'Average price weighted by volume',
                'application': 'Institutional traders use as benchmark; price above VWAP is bullish',
                'viability': 'high'
            }
        ]
        
        insights = []
        
        for indicator in indicators:
            insight_text = f"Indicator: {indicator['name']} - {indicator['application']}"
            
            metadata = {
                'type': 'indicator',
                'source': 'technical_analysis',
                'indicator_name': indicator['name'],
                'viability': indicator['viability'],
                'timestamp': datetime.now().isoformat()
            }
            
            insight_id = self.knowledge_base.add_insight(
                text=insight_text,
                metadata=metadata
            )
            
            insights.append({
                'id': insight_id,
                'text': insight_text,
                'metadata': metadata
            })
        
        logger.info(f"Documented {len(insights)} technical indicators")
        return insights
    
    def run_daily_research(self) -> Dict:
        """
        Run comprehensive daily strategy research.
        
        Returns:
            Summary of research results
        """
        logger.info("Starting daily strategy research...")
        
        all_insights = []
        
        # Research from various sources
        all_insights.extend(self.research_investopedia_strategies())
        all_insights.extend(self.research_reddit_strategies())
        all_insights.extend(self.research_technical_indicators())
        
        # Generate summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_insights': len(all_insights),
            'sources': {
                'investopedia': len([i for i in all_insights if 'investopedia' in i['metadata'].get('source_url', '')]),
                'reddit': len([i for i in all_insights if i['metadata'].get('source', '').startswith('reddit_')]),
                'technical': len([i for i in all_insights if i['metadata'].get('type') == 'indicator'])
            },
            'viability_breakdown': {
                'high': len([i for i in all_insights if i['metadata'].get('viability') == 'high']),
                'medium': len([i for i in all_insights if i['metadata'].get('viability') == 'medium']),
                'low': len([i for i in all_insights if i['metadata'].get('viability') == 'low'])
            }
        }
        
        logger.info(f"Daily research complete: {summary['total_insights']} insights extracted")
        return summary


# Test mode
if __name__ == "__main__":
    print("=== Strategy Researcher Test Mode ===\n")
    
    kb = KnowledgeBase()
    researcher = StrategyResearcher(kb)
    
    # Research technical indicators
    print("Researching technical indicators...")
    indicators = researcher.research_technical_indicators()
    print(f"  Documented {len(indicators)} indicators\n")
    
    # Research Investopedia (limited to avoid excessive scraping in test)
    print("Researching Investopedia strategies...")
    investopedia_insights = researcher.research_investopedia_strategies()
    print(f"  Extracted {len(investopedia_insights)} insights\n")
    
    # Show sample insights
    print("Sample insights:")
    for insight in (indicators + investopedia_insights)[:5]:
        print(f"  - {insight['text'][:80]}...")
        print(f"    Viability: {insight['metadata'].get('viability', 'unknown')}\n")
    
    # Run full daily research
    print("Running full daily research...")
    summary = researcher.run_daily_research()
    print(f"\nResearch Summary:")
    print(f"  Total Insights: {summary['total_insights']}")
    print(f"  Sources:")
    for source, count in summary['sources'].items():
        print(f"    - {source}: {count}")
    print(f"  Viability:")
    for level, count in summary['viability_breakdown'].items():
        print(f"    - {level}: {count}")
