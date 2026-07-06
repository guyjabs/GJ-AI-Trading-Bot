"""
eToro Social Intelligence Scraper (Simulated)
This module simulates scraping eToro's "Popular Investors" to extract what the smartest
retail traders are buying. It acts as a Meta-Copier data feed.
"""

import random
from typing import List, Dict
from ..utils import logger

class EtoroScraper:
    def __init__(self):
        # We simulate finding popular penny stocks and highly volatile assets
        # that top retail traders typically crowd into.
        self._mock_social_pool = [
            "SOFI", "PLTR", "LCID", "RIVN", "HOOD", "CHPT", "F", 
            "NIO", "DKNG", "AMC", "GME", "SNDL", "BB", "TLRY"
        ]
        
        # We also simulate discovering penny cryptos
        self._mock_crypto_pool = [
            "SHIB/USD", "DOGE/USD", "PEPE/USD", "BONK/USD", 
            "FLOKI/USD", "WIF/USD", "ADA/USD", "XRP/USD"
        ]

    def get_top_investor_portfolios(self, limit: int = 10) -> List[Dict]:
        """
        Simulates fetching the exact portfolio composition of the top N 
        most profitable 'Popular Investors' on eToro.
        
        In a production environment, this would use Selenium or an unofficial API 
        wrapper (like fast-etoro) to pull actual live public portfolios.
        """
        logger.info(f"🔍 ETORO: Simulating scrape of top {limit} Popular Investors' portfolios...")
        
        portfolios = []
        for i in range(limit):
            # Simulate a portfolio with 3 to 6 major holdings
            num_holdings = random.randint(3, 6)
            
            # Mix standard stocks with a chance of crypto
            holdings = random.sample(self._mock_social_pool, max(1, num_holdings - 1))
            if random.random() > 0.5:
                holdings.append(random.choice(self._mock_crypto_pool))
                
            # Assign random allocation percentages
            allocations = {}
            remaining = 100.0
            for j, asset in enumerate(holdings):
                if j == len(holdings) - 1:
                    allocations[asset] = round(remaining, 2)
                else:
                    alloc = round(random.uniform(5.0, remaining * 0.7), 2)
                    allocations[asset] = alloc
                    remaining -= alloc
                    
            portfolios.append({
                "investor_id": f"guru_{random.randint(1000, 9999)}",
                "risk_score": random.randint(3, 7),
                "12m_return_pct": round(random.uniform(15.0, 85.0), 2),
                "win_rate_pct": round(random.uniform(35.0, 85.0), 2),
                "max_drawdown_pct": round(random.uniform(5.0, 35.0), 2),
                "active_weeks": random.randint(20, 150),
                "holdings": allocations
            })
            
        return portfolios

    def get_trending_social_stocks(self, min_consensus_threshold: int = 3, require_steady: bool = True) -> List[str]:
        """
        Analyzes the top investor portfolios and returns a list of assets
        that are widely held (appearing in multiple guru portfolios).
        This identifies "Social Consensus" buys before they pump.
        """
        logger.info("🔍 ETORO: Analyzing Social Consensus across top portfolios...")
        
        # We fetch a larger pool so we can filter out the gamblers
        all_portfolios = self.get_top_investor_portfolios(limit=50)
        
        valid_portfolios = []
        for port in all_portfolios:
            if require_steady:
                # Filter out one-hit wonders: 
                # Need steady win rate, low drawdown, and solid history
                if port["win_rate_pct"] < 60.0 or port["max_drawdown_pct"] > 15.0 or port["active_weeks"] < 52:
                    continue
            valid_portfolios.append(port)
            
        logger.info(f"🔥 ETORO: Filtered down to {len(valid_portfolios)} highly steady traders from pool of {len(all_portfolios)}.")
        
        asset_counts = {}
        for port in valid_portfolios:
            for asset in port['holdings'].keys():
                asset_counts[asset] = asset_counts.get(asset, 0) + 1
                
        # Filter for assets held by at least `min_consensus_threshold` steady investors
        consensus_assets = [asset for asset, count in asset_counts.items() if count >= min_consensus_threshold]
        
        # Format cryptos consistently
        consensus_assets = [asset.replace("/", "-") if "/" in asset else asset for asset in consensus_assets]
        
        logger.info(f"🔥 ETORO: Identified {len(consensus_assets)} Social Consensus assets from steady traders: {consensus_assets}")
        return consensus_assets

# Global singleton
etoro_scraper = EtoroScraper()
