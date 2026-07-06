import os
import json
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
import joblib
from src.utils import logger

class QuantModel:
    """
    Hybrid rule-based + XGBoost quantitative model for trading decisions.
    Learns over time as trades complete.
    """
    MODEL_PATH = 'data/quant_model.xgb'
    MIN_TRADES_FOR_ML = 1
    
    FEATURE_NAMES = [
        'rsi_14', 'rsi_divergence', 'macd_histogram', 'macd_crossover',
        'bb_position', 'bb_squeeze', 'sma_20_50_cross', 'price_vs_sma200',
        'atr_pct', 'adx', 'stochastic_k', 'obv_trend', 'volume_ratio',
        'volume_trend', 'pe_ratio', 'peg_ratio', 'revenue_growth',
        'profit_margin', 'vix_level', 'spy_trend', 'macro_regime',
        'news_sentiment', 'news_volume'
    ]

    def __init__(self):
        self.model = None
        self.is_trained = False
        self._load_model()

    def _load_model(self):
        try:
            if os.path.exists(self.MODEL_PATH):
                self.model = XGBClassifier()
                self.model.load_model(self.MODEL_PATH)
                self.is_trained = True
                logger.info(f"Loaded trained XGBoost model from {self.MODEL_PATH}")
        except Exception as e:
            logger.error(f"Error loading QuantModel: {e}")
            self.model = None
            self.is_trained = False

    def _save_model(self):
        try:
            os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
            self.model.save_model(self.MODEL_PATH)
            logger.info(f"Saved trained QuantModel to {self.MODEL_PATH}")
        except Exception as e:
            logger.error(f"Error saving QuantModel: {e}")

    def train(self, trade_history: list) -> bool:
        """
        Train the model using history of trades with features.
        trade_history: list of dicts with 'features' and 'profitable' (bool)
        """
        if len(trade_history) < self.MIN_TRADES_FOR_ML:
            logger.info(f"Not enough trades for ML training ({len(trade_history)}/{self.MIN_TRADES_FOR_ML})")
            return False

        try:
            data = []
            labels = []
            
            for trade in trade_history:
                features = trade.get('features', {})
                if not features:
                    continue
                    
                # Ensure all features are present in correct order
                row = []
                valid = True
                for fname in self.FEATURE_NAMES:
                    val = features.get(fname)
                    if val is None or pd.isna(val):
                        valid = False
                        break
                    row.append(val)
                
                if valid:
                    data.append(row)
                    labels.append(1 if trade.get('profitable') else 0)

            df = pd.DataFrame(data, columns=self.FEATURE_NAMES)
            y = np.array(labels)

            if len(df) < 1:
                logger.info("Insufficient valid feature vectors after cleaning")
                return False

            self.model = XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric='logloss',
                random_state=42
            )
            
            self.model.fit(df, y)
            self.is_trained = True
            self._save_model()
            
            importances = self.get_feature_importance()
            top_feats = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info(f"QuantModel trained successfully. Top features: {top_feats}")
            return True
            
        except Exception as e:
            logger.error(f"Error training QuantModel: {e}")
            return False

    def train_from_file(self, filepath: str) -> bool:
        """
        Loads a JSON file containing a list of trades and trains the model on it.
        """
        import json
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Training file {filepath} not found.")
                return False
                
            with open(filepath, 'r') as f:
                trade_history = json.load(f)
                
            logger.info(f"Loaded {len(trade_history)} trades from {filepath}")
            return self.train(trade_history)
        except Exception as e:
            logger.error(f"Error in train_from_file: {e}")
            return False


    def predict(self, features: dict, mode: str = "standard") -> dict:
        """
        Predict win probability and conviction.
        Returns dict with conviction, probability, and method.
        If mode == 'speculative', ignores standard ML model and uses dedicated rules.
        """
        if mode == "speculative":
            conviction, prob = self._speculative_score(features)
            return {
                'conviction': conviction,
                'probability': prob,
                'method': 'speculative_rules'
            }
        if self.is_trained and self.model is not None:
            try:
                row = [features.get(f, 0.0) for f in self.FEATURE_NAMES]
                df = pd.DataFrame([row], columns=self.FEATURE_NAMES)
                
                # predict_proba returns [[prob_0, prob_1]]
                prob = float(self.model.predict_proba(df)[0][1])
                conviction = max(1.0, min(10.0, 1.0 + prob * 9.0))
                
                return {
                    'conviction': conviction,
                    'probability': prob,
                    'method': 'xgboost'
                }
            except Exception as e:
                logger.error(f"Error in XGBoost prediction: {e}. Falling back to rule-based.")
        
        # Fallback to rule-based
        conviction, prob = self._rule_based_score(features)
        return {
            'conviction': conviction,
            'probability': prob,
            'method': 'rule_based'
        }

    def _speculative_score(self, features: dict) -> tuple:
        """
        Scoring tailored specifically for extreme momentum "leap of faith" trades.
        Reverses typical value-investing safety logic (rewards extreme RSI and Volume).
        """
        score = 0.0
        
        # 1. Volume Anomaly is KING
        vol_ratio = features.get('volume_ratio', 1.0)
        if vol_ratio > 3.0:
            score += 4.0
        elif vol_ratio > 2.0:
            score += 2.0
        elif vol_ratio < 1.0:
            score -= 5.0 # We DO NOT want low volume penny stocks
            
        # 2. Extreme RSI is GOOD here (indicates breakout/squeeze)
        rsi = features.get('rsi_14', 50)
        if rsi > 70:
            score += 2.0
        elif rsi > 60:
            score += 1.0
        elif rsi < 40:
            score -= 2.0 # No falling knives
            
        # 3. Bollinger Band breakouts
        bb_pos = features.get('bb_position', 0.5)
        if bb_pos > 0.9:
            score += 2.0 # Riding the upper band
            
        # 4. News Catalyst
        sentiment = features.get('news_sentiment', 0.0)
        if sentiment > 0.5:
            score += 2.0
            
        # Ignore Fundamentals entirely for these plays
        
        # Clamp and scale
        score = max(-5.0, min(10.0, score))
        prob = (score + 5.0) / 15.0 # Maps -5..10 to 0..1
        conviction = max(1.0, min(10.0, 1.0 + prob * 9.0))
        
        return conviction, prob

    def _rule_based_score(self, features: dict) -> tuple:
        """
        Heuristic scoring mechanism before sufficient data is collected for ML.
        Returns (conviction 1-10, probability 0-1)
        """
        score = 0.0
        
        rsi = features.get('rsi_14', 50)
        if rsi < 30: score += 2.0
        elif 30 <= rsi <= 50: score += 1.0
        elif rsi > 70: score -= 2.0

        macd_cross = features.get('macd_crossover', 0)
        macd_hist = features.get('macd_histogram', 0)
        if macd_cross == 1: score += 2.0
        elif macd_cross == -1: score -= 2.0
        if macd_hist > 0: score += 1.0

        bb_pos = features.get('bb_position', 0.5)
        if bb_pos < 0.2: score += 1.0
        elif bb_pos > 0.8: score -= 1.0

        adx = features.get('adx', 20)
        p_vs_sma200 = features.get('price_vs_sma200', 0)
        if adx > 25 and p_vs_sma200 > 0: score += 2.0
        if adx > 25 and p_vs_sma200 < 0: score -= 1.0

        sma_cross = features.get('sma_20_50_cross', 0)
        if sma_cross == 1: score += 1.0

        vol_ratio = features.get('volume_ratio', 1.0)
        if vol_ratio > 1.5: score += 1.0

        sentiment = features.get('news_sentiment', 0.0)
        score += sentiment * 2.0

        regime = features.get('macro_regime', 0)
        if regime == 1.0: score += 1.0
        elif regime == -1.0: score -= 2.0

        peg = features.get('peg_ratio', 0)
        rev = features.get('revenue_growth', 0)
        if 0 < peg < 1.5: score += 1.0
        if rev > 0.15: score += 1.0

        # Clamp and scale
        score = max(-5.0, min(10.0, score))
        prob = (score + 5.0) / 15.0
        conviction = max(1.0, min(10.0, 1.0 + prob * 9.0))
        
        return conviction, prob

    def get_feature_importance(self) -> dict:
        """Get dict of feature importances if model is trained"""
        if not self.is_trained or self.model is None:
            return {}
        try:
            importances = self.model.feature_importances_
            return {name: float(imp) for name, imp in zip(self.FEATURE_NAMES, importances)}
        except:
            return {}
