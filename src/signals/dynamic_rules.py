def apply_dynamic_rules(features: dict, current_decision: str) -> str:
    rsi = features.get("rsi_14", 0)
    macd_hist = features.get("macd_histogram", 0)
    news_sentiment = features.get("news_sentiment", 0)

    # Rule to hold if RSI indicates overbought conditions
    if rsi > 80 and current_decision == "buy":
        return "hold"
    
    # Rule to hold if MACD histogram is negative
    if macd_hist < 0 and current_decision == "buy":
        return "hold"

    # Rule to hold if news sentiment is not strong enough
    if news_sentiment < 0.6 and current_decision == "buy":
        return "hold"

    return current_decision