"""
Research Archive Manager - Saves research data by date for historical analysis.
"""

import os
import json
from datetime import datetime
from typing import Dict, List

from ..utils import logger

ARCHIVE_DIR = "data/research_archive"

class ResearchArchiver:
    """Manages date-based archiving of research data."""
    
    def __init__(self):
        """Initialize the research archiver."""
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        logger.info("📁 Research archiver initialized")
    
    def get_today_path(self) -> str:
        """Get the archive path for today's date."""
        today = datetime.now().strftime('%Y-%m-%d')
        date_dir = os.path.join(ARCHIVE_DIR, today)
        os.makedirs(date_dir, exist_ok=True)
        return date_dir
    
    def save_news_snapshot(self, articles: List[Dict]):
        """
        Save a snapshot of news articles for today.
        
        Args:
            articles: List of news articles
        """
        try:
            date_dir = self.get_today_path()
            timestamp = datetime.now().strftime('%H-%M-%S')
            filepath = os.path.join(date_dir, f"news_{timestamp}.json")
            
            with open(filepath, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'article_count': len(articles),
                    'articles': articles
                }, f, indent=2)
            
            logger.info(f"💾 Archived {len(articles)} news articles to {filepath}")
        except Exception as e:
            logger.error(f"Error archiving news: {e}")
    
    def save_predictions(self, predictions: List[Dict]):
        """
        Save predictions for today.
        
        Args:
            predictions: List of predictions
        """
        try:
            date_dir = self.get_today_path()
            timestamp = datetime.now().strftime('%H-%M-%S')
            filepath = os.path.join(date_dir, f"predictions_{timestamp}.json")
            
            with open(filepath, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'prediction_count': len(predictions),
                    'predictions': predictions
                }, f, indent=2)
            
            logger.info(f"🔮 Archived {len(predictions)} predictions to {filepath}")
        except Exception as e:
            logger.error(f"Error archiving predictions: {e}")
    
    def save_trends(self, trends: List[Dict]):
        """
        Save detected trends for today.
        
        Args:
            trends: List of trends
        """
        try:
            date_dir = self.get_today_path()
            timestamp = datetime.now().strftime('%H-%M-%S')
            filepath = os.path.join(date_dir, f"trends_{timestamp}.json")
            
            with open(filepath, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'trend_count': len(trends),
                    'trends': trends
                }, f, indent=2)
            
            logger.info(f"📈 Archived {len(trends)} trends to {filepath}")
        except Exception as e:
            logger.error(f"Error archiving trends: {e}")
    
    def save_daily_summary(self, summary: Dict):
        """
        Save end-of-day research summary.
        
        Args:
            summary: Summary dictionary
        """
        try:
            date_dir = self.get_today_path()
            filepath = os.path.join(date_dir, "daily_summary.json")
            
            with open(filepath, 'w') as f:
                json.dump({
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'generated_at': datetime.now().isoformat(),
                    **summary
                }, f, indent=2)
            
            logger.info(f"📋 Saved daily research summary")
        except Exception as e:
            logger.error(f"Error saving daily summary: {e}")
    
    def get_historical_data(self, date: str, data_type: str = 'all') -> List[Dict]:
        """
        Retrieve historical research data for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            data_type: Type of data ('news', 'predictions', 'trends', 'all')
            
        Returns:
            List of data items
        """
        try:
            date_dir = os.path.join(ARCHIVE_DIR, date)
            if not os.path.exists(date_dir):
                logger.warning(f"No archive found for {date}")
                return []
            
            all_data = []
            
            # Get all files matching the data type
            for filename in os.listdir(date_dir):
                if data_type == 'all' or filename.startswith(data_type):
                    filepath = os.path.join(date_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        all_data.append(data)
            
            logger.info(f"📖 Retrieved {len(all_data)} {data_type} records from {date}")
            return all_data
            
        except Exception as e:
            logger.error(f"Error retrieving historical data: {e}")
            return []
    
    def list_available_dates(self) -> List[str]:
        """
        List all dates with archived data.
        
        Returns:
            List of dates in YYYY-MM-DD format
        """
        try:
            dates = [d for d in os.listdir(ARCHIVE_DIR) if os.path.isdir(os.path.join(ARCHIVE_DIR, d))]
            dates.sort(reverse=True)  # Most recent first
            return dates
        except Exception as e:
            logger.error(f"Error listing archive dates: {e}")
            return []
