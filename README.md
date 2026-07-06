# GJ AI Trading Bot: The "Dual-Threat" Autonomous Trading System

## 🚀 System Architecture & Mathematical Models
The **GJ AI Trading Bot** is a fully autonomous, multi-agent AI trading system. It operates on a **"Dual-Threat"** framework, applying strict mathematical screening for standard equities while utilizing behavioral, social, and momentum-driven metrics for high-risk speculative plays.

The pipeline executes through 5 distinct engines:

---

## 1. The Multi-Strategy Screener (`src/screener.py`)
The screener iterates through a universe of assets (S&P 500, Russell 2000, and Crypto) and scores them based on three foundational quantitative models.

### A. Momentum Strategy
Hunts for trend continuation and explosive breakouts.
**Mathematical Criteria:**
* **`market_cap`** > $1B
* **`price`** > $5.00
* **`volume_ratio`** (Current Volume / 20-Day Average Volume) > 1.5x
* **`price_change_5d`** > 5.0%
* **`current_price`** > 50-day Simple Moving Average (SMA)

**Scoring Formula:**
```python
score = (price_change_5d * 5) + ((volume_ratio - 1) * 20)
if price > SMA_50:
    score += ((price - SMA_50) / SMA_50) * 50
if 50 <= RSI_14 <= 70:
    score += 15 # Rewards a healthy trend
elif RSI_14 > 70:
    score -= (RSI_14 - 70) * 1.5 # Penalizes overbought exhaustion
```

### B. Growth Strategy
Focuses on scaling companies with outperforming top and bottom lines.
**Mathematical Criteria:**
* **`market_cap`** > $500M
* **`earnings_growth`** (YoY) > 10% AND **`revenue_growth`** (YoY) > 10%

**Scoring Formula:**
```python
score = (earnings_growth * 100) + (revenue_growth * 80)
if recommendation in ['buy', 'strong_buy']:
    score += 20
```

### C. Value Strategy
Finds cash-cows trading at discounts to their sector peers.
**Mathematical Criteria:**
* Computes industry averages dynamically (`avg_pe`, `avg_peg`, `avg_fcf_share`).
* **`debt_to_equity`** < 0.5
* **`pe_ratio`** < Industry Average
* **`peg_ratio`** < 2.0

**Scoring Formula:**
```python
if pe_ratio < avg_pe: 
    score += (avg_pe - pe_ratio) * 5
if peg_ratio < 2.0: 
    score += (2.0 - peg_ratio) * 20
if fcf_per_share > avg_fcf: 
    score += 30 # Bonus for beating industry average cash flow
```

---

## 2. Speculative & Social Consensus Tracking (`src/research/etoro_scraper.py`)
For Penny Stocks and Cryptos, fundamentals do not matter. The bot ignores P/E and focuses purely on volume, momentum, and Social Consensus.

### The eToro "Smart Money" Filter
The bot queries eToro's "Popular Investors" database to see what top retail traders are buying. However, to filter out gamblers, the bot strictly enforces these metrics before adding an investor to the tracking pool:
* **`win_rate_pct` >= 60.0%**
* **`max_drawdown_pct` <= 15.0%**
* **`active_weeks` >= 52**

If multiple traders in this highly elite subset buy the same speculative asset, it is flagged as a `Social Consensus Asset` and receives a massive +50 point bonus to its momentum score, forcing the bot to pay attention to it.

---

## 3. The GPT-4 Sentiment Engine (`src/ai/sentiment_engine.py`)
News is fetched from **NewsAPI**, **AlphaVantage**, and **Finnhub** (including Cointelegraph RSS for crypto hype).

The bot passes the 15 most recent articles directly to **GPT-4** (via `gpt-4o-mini`), bypassing simple NLP libraries like VADER. 

**The Prompt & Processing:**
The AI is instructed to *"Factor in retail hype from forums heavily for cryptos"* and must return a strict JSON object containing:
1. `sentiment_score`: A continuous float `[-1.0, 1.0]`.
2. `confidence`: A confidence weight `[0.0, 1.0]`.
3. `key_catalysts`: An array of explicit reasons for the pump.
4. `risk_factors`: An array of bearish threats.

---

## 4. The 23-Feature Quant Model (`src/signals/quant_model.py`)
Once an asset passes the screener, it is converted into a 23-dimensional feature vector in `src/signals/signal_generator.py`.

**The 23 Input Features:**
* **Momentum:** `rsi_14`, `rsi_divergence`, `macd_histogram`, `macd_crossover`, `stochastic_k`
* **Volatility:** `bb_position`, `bb_squeeze`, `atr_pct`
* **Trend:** `sma_20_50_cross`, `price_vs_sma200`, `adx`
* **Volume:** `obv_trend`, `volume_ratio`, `volume_trend`
* **Fundamentals:** `pe_ratio`, `peg_ratio`, `revenue_growth`, `profit_margin`
* **Macro:** `vix_level`, `spy_trend`, `macro_regime`
* **AI Sentiment:** `news_sentiment`, `news_volume`

**The XGBoost Engine:**
These 23 features are fed into an **XGBoost Classifier** (`max_depth=4`, `learning_rate=0.05`, `n_estimators=200`, `subsample=0.8`). 
The XGBoost model outputs a raw probability (`0.0` to `1.0`) of the trade being profitable based on historical training data.
* **Conviction Conversion:** `conviction = 1.0 + (probability * 9.0)` (Scaling to a 1-10 score).

*(Note: If running in "Speculative/DeGen" mode, the XGBoost model is bypassed entirely in favor of an extreme-momentum mathematical rule system that rewards riding upper Bollinger bands (`bb_position > 0.9`) and extreme volume anomalies (`volume_ratio > 3.0`)).*

---

## 5. The Self-Learning Loop (`src/self_improvement/improvement_loop.py`)
The system adapts daily. Every completed trade is stored in `data/trade_journal.db`.
1. The bot pulls all historical trades.
2. It extracts the 23-feature vector that was recorded *at the exact moment* the trade was taken.
3. It maps the vector to a binary classification label (`1` if the trade ended in profit, `0` if it took a loss).
4. The XGBoost model is refitted to the new dataset. 

If market regimes shift (e.g., Value investing starts beating Growth, or MACD crossovers stop working), the internal decision trees adapt automatically without human intervention, altering the mathematical weights of the 23 features over time.
