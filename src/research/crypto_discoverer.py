import requests
from typing import List
from src.utils import logger

class CryptoDiscoverer:
    """
    Dynamically discovers trending and unknown cryptos using the CoinGecko API.
    """
    def __init__(self):
        self.session = requests.Session()
        # CoinGecko public trending endpoint
        self.trending_url = "https://api.coingecko.com/api/v3/search/trending"
        
    def get_trending_symbols(self, format_suffix: str = "/USD") -> List[str]:
        """
        Fetches trending coins and formats them for the bot's universe.
        e.g., format_suffix="/USD" outputs ["DOGE/USD", "PEPE/USD"]
        """
        try:
            logger.info("🔍 Discovering trending cryptos via CoinGecko...")
            response = self.session.get(self.trending_url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch trending cryptos. Status: {response.status_code}")
                return []
                
            data = response.json()
            trending_coins = data.get('coins', [])
            
            symbols = []
            for coin_entry in trending_coins:
                coin = coin_entry.get('item', {})
                symbol = coin.get('symbol', '').upper()
                if symbol:
                    formatted_symbol = f"{symbol}{format_suffix}"
                    symbols.append(formatted_symbol)
            
            logger.info(f"✅ Discovered {len(symbols)} trending cryptos: {symbols[:5]}...")
            return symbols
            
        except Exception as e:
            logger.error(f"Error discovering trending cryptos: {e}")
            return []

crypto_discoverer = CryptoDiscoverer()
