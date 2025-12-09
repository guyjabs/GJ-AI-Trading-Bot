import json
import os
from typing import Dict, Any
from src.utils import logger

USER_CONFIG_FILE = 'data/user_config.json'

DEFAULT_METRICS_CONFIG = {
    "momentum": {
        "min_top_gainers_pct": 5,        # Price > 5%
        "min_volume_ratio": 1.5,         # Vol > 1.5x Avg
        "period_vol_comparison": "30d"   # Comparison period
    },
    "value": {
        "min_cashflow_per_share_diff": 0, # Placeholder
        "max_peg_ratio": 2.0,            # PEG < 2.0
        "use_industry_peers": True       # Compare P/E vs Peers
    },
    "growth": {
        "trending_industries": [         # Default industries
            "Software - Infrastructure",
            "Semiconductors",
            "Biotechnology",
            "Solar"
        ],
        "min_earnings_growth": 10        # 10% YoY
    },
    "crypto_bots": [
        {
            "name": "Moonshot",
            "enabled": True,
            "strategy": "moonshot", 
            "symbols": ["DOGE/USD", "SHIB/USD", "SOL/USD", "AVAX/USD", "LTC/USD"],
            "max_position_size_usd": 1000
        },
        {
            "name": "Conservative",
            "enabled": True,
            "strategy": "dip_buy",
            "symbols": ["BTC/USD", "ETH/USD"],
            "max_position_size_usd": 2000
        },
        {
            "name": "Custom",
            "enabled": True,
            "strategy": "custom", 
            "symbols": ["LINK/USD"], # User can edit this list
            "max_position_size_usd": 500
        }
    ]
}

class ConfigManager:
    """
    Manages global user configuration for strategies and metrics.
    Persists to data/user_config.json, sharing file with AlertManager.
    """
    def __init__(self):
        self.metrics = DEFAULT_METRICS_CONFIG.copy()
        self.load_config()

    def load_config(self):
        if os.path.exists(USER_CONFIG_FILE):
            try:
                with open(USER_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    # Merge with defaults
                    saved_metrics = data.get('metrics_config', {})
                    
                    # Deep merge to allow partial updates
                    for strategy, params in saved_metrics.items():
                        if strategy in self.metrics:
                            if isinstance(self.metrics[strategy], dict) and isinstance(params, dict):
                                self.metrics[strategy].update(params)
                            else:
                                self.metrics[strategy] = params # Replace lists/values directly
                        else:
                            self.metrics[strategy] = params
                            
                logger.info("Loaded strategy metrics configuration")
            except Exception as e:
                logger.error(f"Error loading metrics config: {e}")
                self.save_config() # Save defaults if load fails
        else:
            self.save_config()

    def save_config(self):
        """Save metrics to shared config file (preserving alerts)"""
        try:
            data = {}
            # Read existing to preserve alerts/watchlist
            if os.path.exists(USER_CONFIG_FILE):
                with open(USER_CONFIG_FILE, 'r') as f:
                    try:
                        data = json.load(f)
                    except:
                        pass
            
            # Update metrics section
            data['metrics_config'] = self.metrics
            
            with open(USER_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
                
            logger.info("Saved strategy metrics configuration")
        except Exception as e:
            logger.error(f"Error saving metrics config: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        return self.metrics

    def update_metrics(self, new_metrics: Dict[str, Any]):
        """Update strategy configuration"""
        for strategy, params in new_metrics.items():
            if strategy in self.metrics:
                # Special handling for crypto_bots: replace the list if it exists,
                # otherwise update individual bot configs.
                if strategy == "crypto_bots" and isinstance(params, list):
                    self.metrics[strategy] = params
                else:
                    self.metrics[strategy].update(params)
            else:
                self.metrics[strategy] = params # Add new top-level strategy if it doesn't exist
        self.save_config()
        
    def update_bot_config(self, bot_name: str, updates: Dict):
        """Update configuration for a specific bot"""
        bots = self.metrics.get('crypto_bots', [])
        
        updated = False
        for bot in bots:
            if bot.get('name') == bot_name:
                bot.update(updates)
                updated = True
                logger.info(f"Updated config for {bot_name}: {updates}")
                break
        
        if updated:
            self.metrics["crypto_bots"] = bots # Ensure the updated list is set back
            self.save_config()
        else:
            logger.warning(f"Bot {bot_name} not found in config")

# Global instance
config_manager = ConfigManager()
