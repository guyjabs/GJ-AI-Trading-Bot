import os
import json
from src.utils import logger
from src.api.openai import make_ai_request
from config import OPENAI_MODEL_NAME

class AIOptimizer:
    """
    Advanced AI Code Self-Improvement.
    Analyzes losing trades to write dynamic, hard-coded rules into dynamic_rules.py.
    """
    RULES_FILE = 'src/signals/dynamic_rules.py'
    
    def __init__(self):
        pass
        
    def generate_dynamic_rules(self, losing_trades: list):
        """
        Takes a list of losing trades, feeds them to GPT-4, and generates
        a new version of dynamic_rules.py to prevent these losses.
        """
        if not losing_trades:
            logger.info("No losing trades to analyze.")
            return False
            
        logger.info(f"🤖 AI Optimizer analyzing {len(losing_trades)} losing trades to write dynamic rules...")
        
        # Prepare the context
        trades_context = []
        for t in losing_trades[:50]: # limit to recent 50 to save tokens
            # t is a dict from trade journal
            features = t.get('feature_vector', {})
            trades_context.append({
                'symbol': t.get('symbol'),
                'decision': t.get('decision', 'buy'),
                'pnl_pct': t.get('pnl_pct', 0),
                'features': features
            })
            
        prompt = f"""
You are an expert algorithmic trading engineer.
Your system recently executed trades that resulted in losses.
Here is a sample of the losing trades (including the feature vector at the time of the trade):
{json.dumps(trades_context, indent=2)}

Your task is to write Python code to prevent these types of losses in the future.
Write a python file with a single function: `apply_dynamic_rules(features: dict, current_decision: str) -> str`
This function should take the dictionary of features and the model's current decision ('buy', 'sell', 'short', 'cover', 'hold')
and return the updated decision (e.g., if you detect a trap, return 'hold').

Only output valid Python code starting with ```python and ending with ```.
Do not explain. Just the code.
        """
        
        try:
            messages = [
                {"role": "system", "content": "You are a Python AI Coding Agent."},
                {"role": "user", "content": prompt}
            ]
            response = make_ai_request(messages, model=OPENAI_MODEL_NAME)
            
            # Extract python code
            content = response.choices[0].message.content
            if '```python' in content:
                code = content.split('```python')[1].split('```')[0].strip()
            elif '```' in content:
                code = content.split('```')[1].split('```')[0].strip()
            else:
                code = content.strip()
                
            if "def apply_dynamic_rules" in code:
                with open(self.RULES_FILE, 'w') as f:
                    f.write(code)
                logger.info(f"✅ Generated new dynamic rules at {self.RULES_FILE}")
                return True
            else:
                logger.error("AI did not output the expected function.")
                return False
                
        except Exception as e:
            logger.error(f"Failed to generate dynamic rules: {e}")
            return False
