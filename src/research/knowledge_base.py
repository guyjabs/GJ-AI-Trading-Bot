"""
Knowledge Base system using ChromaDB for semantic search and storage.
Stores insights, trends, predictions, and learned patterns.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

from ..utils import logger

# Storage paths
KNOWLEDGE_BASE_DIR = "data/knowledge_base"
CHROMADB_DIR = os.path.join(KNOWLEDGE_BASE_DIR, "chromadb")
INSIGHTS_FILE = os.path.join(KNOWLEDGE_BASE_DIR, "insights.json")
PREDICTIONS_FILE = os.path.join(KNOWLEDGE_BASE_DIR, "predictions.json")
TRENDS_FILE = os.path.join(KNOWLEDGE_BASE_DIR, "trends.json")


class KnowledgeBase:
    """Vector database-backed knowledge management system."""
    
    def __init__(self):
        """Initialize knowledge base with ChromaDB."""
        # Create directories
        os.makedirs(CHROMADB_DIR, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=CHROMADB_DIR,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collections
        self.insights_collection = self.client.get_or_create_collection(
            name="insights",
            metadata={"description": "Market insights extracted from news"}
        )
        
        self.trends_collection = self.client.get_or_create_collection(
            name="trends",
            metadata={"description": "Detected market trends and patterns"}
        )
        
        self.predictions_collection = self.client.get_or_create_collection(
            name="predictions",
            metadata={"description": "Historical predictions and outcomes"}
        )
        
        logger.info("Knowledge base initialized")
    
    def add_insight(self, text: str, metadata: Dict, insight_id: Optional[str] = None) -> str:
        """
        Add an insight to the knowledge base.
        
        Args:
            text: The insight text
            metadata: Metadata (symbol, source, timestamp, sentiment, etc.)
            insight_id: Optional custom ID, otherwise auto-generated
            
        Returns:
            The insight ID
        """
        if not insight_id:
            insight_id = f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Add timestamp if not present
        if 'timestamp' not in metadata:
            metadata['timestamp'] = datetime.now().isoformat()
        
        try:
            self.insights_collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[insight_id]
            )
            logger.debug(f"Added insight: {insight_id}")
            return insight_id
        except Exception as e:
            logger.error(f"Error adding insight: {e}")
            return None
    
    def add_trend(self, text: str, metadata: Dict, trend_id: Optional[str] = None) -> str:
        """
        Add a trend to the knowledge base.
        
        Args:
            text: The trend description
            metadata: Metadata (type, symbols, strength, timeframe, etc.)
            trend_id: Optional custom ID
            
        Returns:
            The trend ID
        """
        if not trend_id:
            trend_id = f"trend_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        if 'timestamp' not in metadata:
            metadata['timestamp'] = datetime.now().isoformat()
        
        try:
            self.trends_collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[trend_id]
            )
            logger.debug(f"Added trend: {trend_id}")
            return trend_id
        except Exception as e:
            logger.error(f"Error adding trend: {e}")
            return None
    
    def add_prediction(self, text: str, metadata: Dict, prediction_id: Optional[str] = None) -> str:
        """
        Add a prediction to the knowledge base.
        
        Args:
            text: The prediction description
            metadata: Metadata (symbol, direction, confidence, timeframe, reasoning, etc.)
            prediction_id: Optional custom ID
            
        Returns:
            The prediction ID
        """
        if not prediction_id:
            prediction_id = f"prediction_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        if 'timestamp' not in metadata:
            metadata['timestamp'] = datetime.now().isoformat()
        
        # Set default status
        if 'status' not in metadata:
            metadata['status'] = 'active'
        
        try:
            self.predictions_collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[prediction_id]
            )
            logger.debug(f"Added prediction: {prediction_id}")
            return prediction_id
        except Exception as e:
            logger.error(f"Error adding prediction: {e}")
            return None
    
    def search_insights(self, query: str, n_results: int = 10, filter_dict: Dict = None) -> List[Dict]:
        """
        Search insights using semantic similarity.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_dict: Optional metadata filter
            
        Returns:
            List of matching insights
        """
        try:
            results = self.insights_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_dict
            )
            
            insights = []
            for i in range(len(results['ids'][0])):
                insights.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
            
            return insights
        except Exception as e:
            logger.error(f"Error searching insights: {e}")
            return []
    
    def search_trends(self, query: str, n_results: int = 10, filter_dict: Dict = None) -> List[Dict]:
        """Search trends using semantic similarity."""
        try:
            results = self.trends_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_dict
            )
            
            trends = []
            for i in range(len(results['ids'][0])):
                trends.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
            
            return trends
        except Exception as e:
            logger.error(f"Error searching trends: {e}")
            return []
    
    def get_insights_for_symbol(self, symbol: str, limit: int = 20) -> List[Dict]:
        """
        Get all insights for a specific symbol.
        
        Args:
            symbol: Stock or crypto symbol
            limit: Maximum number of insights to return
            
        Returns:
            List of insights
        """
        try:
            # ChromaDB doesn't support direct filtering without query, so we use a generic query
            results = self.insights_collection.query(
                query_texts=[symbol],
                n_results=limit,
                where={"symbol": symbol}
            )
            
            insights = []
            for i in range(len(results['ids'][0])):
                insights.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i]
                })
            
            return insights
        except Exception as e:
            logger.error(f"Error getting insights for {symbol}: {e}")
            return []
    
    def get_active_predictions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all active predictions, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter by
            
        Returns:
            List of active predictions
        """
        try:
            filter_dict = {"status": "active"}
            if symbol:
                filter_dict["symbol"] = symbol
            
            # Get all predictions (ChromaDB requires a query)
            results = self.predictions_collection.query(
                query_texts=["prediction"],
                n_results=100,
                where=filter_dict
            )
            
            predictions = []
            for i in range(len(results['ids'][0])):
                predictions.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i]
                })
            
            return predictions
        except Exception as e:
            logger.error(f"Error getting active predictions: {e}")
            return []
    
    def update_prediction_outcome(self, prediction_id: str, outcome: str, actual_result: Dict):
        """
        Update a prediction with its actual outcome.
        
        Args:
            prediction_id: The prediction ID
            outcome: 'correct', 'incorrect', or 'partial'
            actual_result: Dictionary with actual price movement, etc.
        """
        try:
            # Get the prediction
            result = self.predictions_collection.get(ids=[prediction_id])
            
            if not result['ids']:
                logger.warning(f"Prediction {prediction_id} not found")
                return
            
            # Update metadata
            metadata = result['metadatas'][0]
            metadata['status'] = 'completed'
            metadata['outcome'] = outcome
            metadata['actual_result'] = json.dumps(actual_result)
            metadata['completed_at'] = datetime.now().isoformat()
            
            # Update in collection
            self.predictions_collection.update(
                ids=[prediction_id],
                metadatas=[metadata]
            )
            
            logger.info(f"Updated prediction {prediction_id} with outcome: {outcome}")
        except Exception as e:
            logger.error(f"Error updating prediction outcome: {e}")
    
    def get_prediction_accuracy(self, days: int = 30) -> Dict:
        """
        Calculate prediction accuracy over the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with accuracy statistics
        """
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get completed predictions
            results = self.predictions_collection.query(
                query_texts=["prediction"],
                n_results=1000,
                where={"status": "completed"}
            )
            
            total = 0
            correct = 0
            incorrect = 0
            partial = 0
            
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i]
                
                # Check if within time range
                if metadata.get('timestamp', '') < cutoff:
                    continue
                
                total += 1
                outcome = metadata.get('outcome', 'unknown')
                
                if outcome == 'correct':
                    correct += 1
                elif outcome == 'incorrect':
                    incorrect += 1
                elif outcome == 'partial':
                    partial += 1
            
            accuracy = (correct / total * 100) if total > 0 else 0
            
            return {
                'total': total,
                'correct': correct,
                'incorrect': incorrect,
                'partial': partial,
                'accuracy': accuracy,
                'period_days': days
            }
        except Exception as e:
            logger.error(f"Error calculating prediction accuracy: {e}")
            return {'total': 0, 'correct': 0, 'incorrect': 0, 'partial': 0, 'accuracy': 0}
    
    def get_recent_trends(self, limit: int = 10, trend_type: Optional[str] = None) -> List[Dict]:
        """
        Get recent trends, optionally filtered by type.
        
        Args:
            limit: Maximum number of trends to return
            trend_type: Optional trend type filter (e.g., 'momentum', 'sector_rotation')
            
        Returns:
            List of recent trends
        """
        try:
            filter_dict = {}
            if trend_type:
                filter_dict['type'] = trend_type
            
            results = self.trends_collection.query(
                query_texts=["trend"],
                n_results=limit,
                where=filter_dict if filter_dict else None
            )
            
            trends = []
            for i in range(len(results['ids'][0])):
                trends.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i]
                })
            
            # Sort by timestamp (newest first)
            trends.sort(key=lambda x: x['metadata'].get('timestamp', ''), reverse=True)
            
            return trends
        except Exception as e:
            logger.error(f"Error getting recent trends: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics."""
        try:
            return {
                'insights_count': self.insights_collection.count(),
                'trends_count': self.trends_collection.count(),
                'predictions_count': self.predictions_collection.count(),
                'storage_path': CHROMADB_DIR
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def export_to_json(self):
        """Export knowledge base to JSON files for backup."""
        try:
            # Export insights
            insights_result = self.insights_collection.get()
            insights_data = []
            for i in range(len(insights_result['ids'])):
                insights_data.append({
                    'id': insights_result['ids'][i],
                    'text': insights_result['documents'][i],
                    'metadata': insights_result['metadatas'][i]
                })
            
            with open(INSIGHTS_FILE, 'w') as f:
                json.dump(insights_data, f, indent=2)
            
            # Export trends
            trends_result = self.trends_collection.get()
            trends_data = []
            for i in range(len(trends_result['ids'])):
                trends_data.append({
                    'id': trends_result['ids'][i],
                    'text': trends_result['documents'][i],
                    'metadata': trends_result['metadatas'][i]
                })
            
            with open(TRENDS_FILE, 'w') as f:
                json.dump(trends_data, f, indent=2)
            
            # Export predictions
            predictions_result = self.predictions_collection.get()
            predictions_data = []
            for i in range(len(predictions_result['ids'])):
                predictions_data.append({
                    'id': predictions_result['ids'][i],
                    'text': predictions_result['documents'][i],
                    'metadata': predictions_result['metadatas'][i]
                })
            
            with open(PREDICTIONS_FILE, 'w') as f:
                json.dump(predictions_data, f, indent=2)
            
            logger.info("Knowledge base exported to JSON files")
        except Exception as e:
            logger.error(f"Error exporting knowledge base: {e}")


# Test mode
if __name__ == "__main__":
    print("=== Knowledge Base Test Mode ===\n")
    
    kb = KnowledgeBase()
    
    # Show stats
    stats = kb.get_stats()
    print(f"Knowledge Base Stats:")
    print(f"  Insights: {stats.get('insights_count', 0)}")
    print(f"  Trends: {stats.get('trends_count', 0)}")
    print(f"  Predictions: {stats.get('predictions_count', 0)}")
    print(f"  Storage: {stats.get('storage_path', 'Unknown')}\n")
    
    # Add sample insight
    print("Adding sample insight...")
    insight_id = kb.add_insight(
        text="Tech stocks rallying on positive AI earnings reports",
        metadata={
            'symbol': 'AAPL',
            'source': 'newsapi',
            'sentiment': 0.8,
            'category': 'earnings'
        }
    )
    print(f"  Added: {insight_id}\n")
    
    # Add sample trend
    print("Adding sample trend...")
    trend_id = kb.add_trend(
        text="Bitcoin showing strong correlation with tech stocks this week",
        metadata={
            'type': 'correlation',
            'symbols': ['BTC', 'AAPL', 'MSFT'],
            'strength': 0.75,
            'timeframe': '1week'
        }
    )
    print(f"  Added: {trend_id}\n")
    
    # Add sample prediction
    print("Adding sample prediction...")
    prediction_id = kb.add_prediction(
        text="AAPL likely to rise 2-3% in next 3 days based on positive earnings sentiment",
        metadata={
            'symbol': 'AAPL',
            'direction': 'up',
            'confidence': 0.75,
            'timeframe_days': 3,
            'reasoning': 'Strong earnings, positive news sentiment, technical momentum'
        }
    )
    print(f"  Added: {prediction_id}\n")
    
    # Search insights
    print("Searching insights for 'tech stocks'...")
    results = kb.search_insights("tech stocks", n_results=5)
    print(f"  Found {len(results)} results")
    for r in results:
        print(f"    - {r['text'][:80]}...")
    print()
    
    # Get insights for symbol
    print("Getting insights for AAPL...")
    aapl_insights = kb.get_insights_for_symbol('AAPL')
    print(f"  Found {len(aapl_insights)} insights")
    for insight in aapl_insights[:3]:
        print(f"    - {insight['text']}")
    print()
    
    # Get active predictions
    print("Getting active predictions...")
    predictions = kb.get_active_predictions()
    print(f"  Found {len(predictions)} active predictions")
    for pred in predictions:
        print(f"    - {pred['text'][:80]}...")
        print(f"      Confidence: {pred['metadata'].get('confidence', 'N/A')}")
    print()
    
    # Export to JSON
    print("Exporting knowledge base to JSON...")
    kb.export_to_json()
    print("  Export complete\n")
    
    # Show final stats
    stats = kb.get_stats()
    print(f"Final Stats:")
    print(f"  Insights: {stats.get('insights_count', 0)}")
    print(f"  Trends: {stats.get('trends_count', 0)}")
    print(f"  Predictions: {stats.get('predictions_count', 0)}")
