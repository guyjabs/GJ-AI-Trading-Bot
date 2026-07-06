from datetime import datetime
from src.utils import logger
from src.signals.signal_generator import SignalGenerator
from src.signals.quant_model import QuantModel
from src.ai.sentiment_engine import SentimentEngine

class AIBrain:
    """
    The Intelligence Layer (Overhauled).
    Now uses QuantModel (XGBoost/Rule-based) instead of raw LLM guessing.
    Only uses LLMs for sentiment feature extraction.
    """
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.quant_model = QuantModel()
        self.sentiment_engine = SentimentEngine()

    def analyze(self, account_info, portfolio, candidates, macro_context=None, fundamental_data=None):
        """
        Generates trading decisions based on statistical signals and model predictions.
        """
        logger.info("🧠 Brain Processing Market Data using Quant Engine...")
        
        valid_decisions = []
        macro_context = macro_context or {}
        fundamental_data = fundamental_data or {}
        
        # Determine all symbols we need to analyze
        symbols_to_evaluate = set()
        for sym in portfolio.keys():
            symbols_to_evaluate.add(sym)
        for sym in candidates.keys():
            symbols_to_evaluate.add(sym)
            
        # We process in batches where possible, but here we process one by one
        # to handle the individual price data structures the current app passes.
        
        for symbol in symbols_to_evaluate:
            try:
                # 1. Fetch Sentiment Feature
                sentiment_data = self.sentiment_engine.get_sentiment(symbol)
                
                # 2. Prepare Price Data (Current app passes price info in candidates/portfolio dicts)
                # It usually looks like candidates[symbol] = {'current_price': x, 'history': df, ...}
                price_info = candidates.get(symbol) or portfolio.get(symbol, {})
                
                # 3. Compute Features
                features = self.signal_generator.compute_features(
                    symbol=symbol,
                    price_data=price_info,
                    macro_context=macro_context,
                    fundamental_data=fundamental_data.get(symbol, {}),
                    sentiment_data=sentiment_data
                )
                
                # 4. Predict
                mode = price_info.get('mode', 'standard')
                prediction = self.quant_model.predict(features, mode=mode)
                prob = prediction.get('probability', 0.0)
                conviction = prediction.get('conviction', 5.0)
                
                # 5. Make Decision Logic
                decision = 'hold'
                reasoning = f"Prob: {prob:.2f}, Conviction: {conviction:.1f}, Method: {prediction.get('method')}"
                
                is_holding_long = symbol in portfolio and portfolio[symbol].get('quantity', 0) > 0
                is_holding_short = symbol in portfolio and portfolio[symbol].get('quantity', 0) < 0
                
                if prob > 0.65:
                    if is_holding_short:
                        decision = 'cover'
                    elif not is_holding_long:
                        decision = 'buy'
                        
                elif prob < 0.35:
                    if is_holding_long:
                        decision = 'sell'
                    elif not is_holding_short and mode != 'speculative' and price_info.get('type') != 'crypto':
                        # Short selling: Only for non-crypto, non-speculative assets with strong bearish signals
                        decision = 'short'
                
                # Check for weaker sell signal if holding long
                elif prob < 0.45 and is_holding_long:
                    decision = 'sell'
                
                # Check for weaker cover signal if holding short
                elif prob > 0.55 and is_holding_short:
                    decision = 'cover'
                
                # 6. Apply AI-Generated Dynamic Rules
                try:
                    from src.signals.dynamic_rules import apply_dynamic_rules
                    decision = apply_dynamic_rules(features, decision)
                except Exception as e:
                    logger.error(f"Failed to apply dynamic rules for {symbol}: {e}")
                
                if decision != 'hold' or symbol in portfolio:
                    valid_decisions.append({
                        'symbol': symbol,
                        'decision': decision,
                        'conviction': conviction,
                        'reasoning': reasoning,
                        'features': features, # Pass features downstream for ML learning loop!
                        'mode': mode
                    })
                    
            except Exception as e:
                logger.error(f"Error evaluating {symbol} in brain: {e}")
                
        return valid_decisions
