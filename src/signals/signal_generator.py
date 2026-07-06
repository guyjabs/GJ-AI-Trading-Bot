from src.indicators import (
    compute_rsi,
    compute_macd,
    compute_bollinger_bands,
    compute_atr,
    compute_adx,
    compute_stochastic,
    compute_obv_trend,
    compute_volume_ratio,
    compute_volume_trend,
    compute_rsi_divergence,
    compute_macd_crossover,
    compute_sma
)
from src.utils import logger
import pandas as pd

class SignalGenerator:
    """
    Computes a 23-feature vector for any stock/crypto symbol based on price,
    macro context, fundamentals, and sentiment.
    """
    def __init__(self):
        pass

    def compute_features(self, symbol: str, price_data: dict, macro_context: dict = None, fundamental_data: dict = None, sentiment_data: dict = None) -> dict:
        """
        Computes all 23 features. Returns a dict of features with float values.
        """
        features = {}
        macro_context = macro_context or {}
        fundamental_data = fundamental_data or {}
        sentiment_data = sentiment_data or {}
        
        # Default fallback dict in case of errors
        default_features = {
            'rsi_14': 50.0,
            'rsi_divergence': 0.0,
            'macd_histogram': 0.0,
            'macd_crossover': 0.0,
            'bb_position': 0.5,
            'bb_squeeze': 0.0,
            'sma_20_50_cross': 0.0,
            'price_vs_sma200': 0.0,
            'atr_pct': 0.0,
            'adx': 20.0,
            'stochastic_k': 50.0,
            'obv_trend': 0.0,
            'volume_ratio': 1.0,
            'volume_trend': 0.0,
            'pe_ratio': 0.0,
            'peg_ratio': 0.0,
            'revenue_growth': 0.0,
            'profit_margin': 0.0,
            'vix_level': 20.0,
            'spy_trend': 0.0,
            'macro_regime': 0.0,
            'news_sentiment': 0.0,
            'news_volume': 0.0
        }

        try:
            history = price_data.get('history')
            if history is None or history.empty:
                logger.warning(f"No history data for {symbol}, using default features.")
                return default_features

            close = history['Close']
            high = history['High']
            low = history['Low']
            volume = history.get('Volume')
            current_price = float(price_data.get('price', close.iloc[-1]))
            is_crypto = price_data.get('type') == 'crypto'

            # 1. RSI
            try:
                rsi_series = compute_rsi(close)
                features['rsi_14'] = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0
            except: features['rsi_14'] = 50.0

            # 2. RSI Divergence
            try:
                rsi_div = compute_rsi_divergence(close)
                features['rsi_divergence'] = float(rsi_div.iloc[-1]) if not rsi_div.empty else 0.0
            except: features['rsi_divergence'] = 0.0

            # 3 & 4. MACD
            try:
                macd_df = compute_macd(close)
                features['macd_histogram'] = float(macd_df['histogram'].iloc[-1]) if not macd_df.empty else 0.0
                macd_cross = compute_macd_crossover(close)
                features['macd_crossover'] = float(macd_cross.iloc[-1]) if not macd_cross.empty else 0.0
            except: 
                features['macd_histogram'] = 0.0
                features['macd_crossover'] = 0.0

            # 5 & 6. Bollinger Bands
            try:
                bb_df = compute_bollinger_bands(close)
                pct_b = float(bb_df['pct_b'].iloc[-1]) if not bb_df.empty else 0.5
                features['bb_position'] = max(0.0, min(1.0, pct_b))
                features['bb_squeeze'] = float(bb_df['width'].iloc[-1]) if not bb_df.empty else 0.0
            except:
                features['bb_position'] = 0.5
                features['bb_squeeze'] = 0.0

            # 7 & 8. SMAs
            try:
                sma20 = compute_sma(close, 20).iloc[-1]
                sma50 = compute_sma(close, 50).iloc[-1]
                features['sma_20_50_cross'] = 1.0 if sma20 > sma50 else -1.0
                
                sma200 = compute_sma(close, 200).iloc[-1]
                features['price_vs_sma200'] = float((current_price - sma200) / sma200) if sma200 > 0 else 0.0
            except:
                features['sma_20_50_cross'] = 0.0
                features['price_vs_sma200'] = 0.0

            # 9. ATR
            try:
                atr = compute_atr(high, low, close).iloc[-1]
                features['atr_pct'] = float(atr / current_price) if current_price > 0 else 0.0
            except: features['atr_pct'] = 0.0

            # 10. ADX
            try:
                adx_df = compute_adx(high, low, close)
                features['adx'] = float(adx_df['adx'].iloc[-1]) if not adx_df.empty else 20.0
            except: features['adx'] = 20.0

            # 11. Stochastic
            try:
                stoch_df = compute_stochastic(high, low, close)
                features['stochastic_k'] = float(stoch_df['k'].iloc[-1]) if not stoch_df.empty else 50.0
            except: features['stochastic_k'] = 50.0

            # Volume features
            if volume is not None and not volume.empty:
                try:
                    obv_tr = compute_obv_trend(close, volume)
                    features['obv_trend'] = float(obv_tr.iloc[-1]) if not obv_tr.empty else 0.0
                except: features['obv_trend'] = 0.0
                
                try:
                    vol_rat = compute_volume_ratio(volume)
                    features['volume_ratio'] = float(vol_rat.iloc[-1]) if not vol_rat.empty else 1.0
                except: features['volume_ratio'] = 1.0
                
                try:
                    vol_tr = compute_volume_trend(volume)
                    features['volume_trend'] = float(vol_tr.iloc[-1]) if not vol_tr.empty else 0.0
                except: features['volume_trend'] = 0.0
            else:
                features['obv_trend'] = 0.0
                features['volume_ratio'] = 1.0
                features['volume_trend'] = 0.0

            # Fundamentals
            def safe_float(val, default=0.0):
                try: return float(val) if val not in [None, 'None', 'N/A', ''] else default
                except: return default
            
            features['pe_ratio'] = safe_float(fundamental_data.get('pe_ratio')) if not is_crypto else 0.0
            features['peg_ratio'] = safe_float(fundamental_data.get('peg_ratio')) if not is_crypto else 0.0
            features['revenue_growth'] = safe_float(fundamental_data.get('revenue_growth_yoy')) if not is_crypto else 0.0
            features['profit_margin'] = safe_float(fundamental_data.get('profit_margin')) if not is_crypto else 0.0

            # Macro
            features['vix_level'] = float(macro_context.get('vix', 20.0))
            features['spy_trend'] = float(macro_context.get('spy_vs_sma50_pct', 0.0))
            features['macro_regime'] = float(macro_context.get('regime_numeric', 0.0))

            # Sentiment
            features['news_sentiment'] = float(sentiment_data.get('sentiment_score', 0.0))
            features['news_volume'] = float(sentiment_data.get('news_volume', 0.0))

            # Fill any missing with default just in case
            for k, v in default_features.items():
                if k not in features or pd.isna(features[k]):
                    features[k] = v

            return features
            
        except Exception as e:
            logger.error(f"Error computing features for {symbol}: {e}")
            return default_features

    def compute_features_batch(self, symbols: list, all_price_data: dict, macro_context: dict = None, all_fundamentals: dict = None, all_sentiments: dict = None) -> dict:
        """
        Batch process features for multiple symbols
        """
        results = {}
        all_fundamentals = all_fundamentals or {}
        all_sentiments = all_sentiments or {}
        
        for symbol in symbols:
            price_data = all_price_data.get(symbol)
            if not price_data:
                continue
                
            fund_data = all_fundamentals.get(symbol, {})
            sent_data = all_sentiments.get(symbol, {})
            
            results[symbol] = self.compute_features(
                symbol, price_data, macro_context, fund_data, sent_data
            )
            
        return results
