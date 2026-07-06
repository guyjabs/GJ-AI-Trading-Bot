
import requests
from src.utils import logger
from config import ALPHAVANTAGE_API_KEY

class Fundamentalist:
    """
    The 'Lynch' Module.
    Fetches fundamental data to filter out garbage.
    """
    def __init__(self):
        self.api_key = ALPHAVANTAGE_API_KEY
        self.base_url = "https://www.alphavantage.co/query"

    def get_fundamentals(self, symbol):
        """
        Fetch Overview data (PE, PEG, Revenue Growth).
        """
        if not self.api_key:
            return {}
            
        try:
            url = f"{self.base_url}?function=OVERVIEW&symbol={symbol}&apikey={self.api_key}"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if "Symbol" not in data:
                return {}
                
            return {
                'pe_ratio': data.get('PERatio', 'N/A'),
                'peg_ratio': data.get('PEGRatio', 'N/A'),
                'revenue_growth_yoy': data.get('QuarterlyRevenueGrowthYOY', 'N/A'),
                'sector': data.get('Sector', 'Unknown')
            }
        except Exception as e:
            logger.error(f"Fundamental Error {symbol}: {e}")
            return {}
