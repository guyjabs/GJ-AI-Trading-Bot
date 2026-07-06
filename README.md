# GJ AI Trading Bot: The "Dual-Threat" Autonomous Trading System

## 🚀 System Overview
The **GJ AI Trading Bot** is a fully autonomous, multi-agent AI trading system designed to navigate modern financial markets. Rather than relying entirely on slow, traditional financial models, this bot was engineered from the ground up with a **"Dual-Threat"** philosophy:

1. **The Steady Quant:** A highly mathematical, risk-averse engine that trades blue-chip stocks and top-tier cryptos based on deep fundamental and technical analysis.
2. **The "Smart Money" Speculator:** A highly aggressive engine that tracks viral retail momentum, scrapes crypto forums, and monitors the portfolios of top eToro traders to execute high-conviction "DeGen" plays right as the hype begins.

The system is fully self-learning. Every night, it reviews its own trades, calculates its win rate, and retrains its **XGBoost Machine Learning Model** to adapt to shifting market conditions.

---

## 🧠 Core Architecture & Intelligence

### 1. The Multi-Strategy Screener (`src/screener.py`)
The bot does not randomly look at tickers. It runs a multi-layered screening pipeline across the entire S&P 500, Russell 2000, and major Crypto markets to filter down thousands of assets into a curated watchlist of ~20 actionable setups.
- **Momentum Strategy:** Looks for explosive volume anomalies (>1.5x average) and RSI breakouts.
- **Growth Strategy:** Filters for companies with >10% EPS growth and >15% revenue growth.
- **Value Strategy:** Scans for cash-cows with low P/E ratios and high Free Cash Flow relative to industry peers.
- **Speculative Strategy:** Explicitly hunts for sub-$10 penny stocks and altcoins experiencing massive, sudden volume spikes.

### 2. Social Consensus Tracking (`src/research/etoro_scraper.py`)
To prevent buying into fake hype, the bot uses an **eToro Meta-Copier**.
- It continuously scrapes the portfolios of eToro's "Popular Investors".
- It filters out the gamblers by enforcing strict criteria: only tracking traders with a **>60% Win Rate**, **<15% Max Drawdown**, and at least **52 weeks** of history.
- When multiple "smart money" steady traders quietly buy the same asset, the bot artificially boosts that asset's conviction score.

### 3. GPT-4 Sentiment & Catalyst Engine (`src/ai/sentiment_engine.py`)
The bot reads the news like a human analyst.
- It aggregates thousands of articles daily across **NewsAPI**, **AlphaVantage**, and **Finnhub**.
- For crypto, it explicitly scrapes **Cointelegraph RSS** and niche crypto blogs to detect retail hype.
- The top 15 most relevant articles/forum posts for an asset are sent to **GPT-4**.
- GPT-4 is prompted to heavily factor in "retail hype" and return a numerical `sentiment_score` (-1.0 to 1.0), along with a structured list of key catalysts and risk factors.

### 4. The XGBoost Quant Model (`src/signals/quant_model.py`)
After the Screener and Sentiment Engine find a target, the data is passed to the Quant Model.
- A 23-feature vector is generated for every ticker, combining technicals (RSI, MACD, Bollinger Bands, Volume Trend), fundamentals (P/E, Revenue Growth), Macro (VIX, SPY trend), and News Sentiment.
- An **XGBoost Classifier** evaluates this vector and outputs a strict probability of the trade being profitable.
- If the probability is too low, the bot rejects the trade and holds cash.

### 5. The Self-Learning Loop (`src/self_improvement/improvement_loop.py`)
The bot gets smarter every single day.
- Every executed trade (both simulated and live) is logged into `data/trade_journal.db`.
- Once the bot accrues enough trades, it triggers a **Granular Retraining Event**.
- It feeds its past winners and losers back into the XGBoost algorithm, adjusting its weights dynamically. If MACD crossovers stop working in a sideways market, the bot will mathematically demote MACD and prioritize RSI automatically.

---

## 🛠 Project Structure

```text
GJ-AI-Trading-Bot/
├── main.py                     # Entry point for single AI decision tests
├── main2.py                    # Multi-agent coordination and decision pipeline
├── run_legendary_sim.py        # 1-year historical simulation script
├── config.py                   # API Keys and System Configurations
├── data/                       
│   ├── trade_journal.db        # SQLite database of all historical trades
│   └── quant_model.xgb         # The trained XGBoost machine learning model
├── src/
│   ├── ai/
│   │   ├── sentiment_engine.py # GPT-4 news analysis
│   │   ├── macro_analyst.py    # Market-wide health checks (SPY/VIX)
│   │   └── fundamentalist.py   # Deep financial analysis
│   ├── research/
│   │   ├── news_aggregator.py  # API fetchers for Finnhub/AlphaVantage
│   │   └── etoro_scraper.py    # Smart Money social consensus tracking
│   ├── screener.py             # Stock universe filtering
│   ├── signals/
│   │   ├── signal_generator.py # 23-feature math vector generation
│   │   └── quant_model.py      # XGBoost prediction model
│   ├── self_improvement/
│   │   └── improvement_loop.py # The nightly learning and retraining cycle
│   └── execution/
│       └── executor.py         # Broker integration for final execution
└── requirements.txt            # Python dependencies
```

## ⚙️ Setup & Execution

**1. Clone & Install**
```bash
git clone <repository>
cd GJ-AI-Trading-Bot
pip install -r requirements.txt
```

**2. API Configuration**
Rename `config.py.example` to `config.py` and input your keys:
- OpenAI API Key (For Sentiment Analysis)
- Alpaca API Key (For Market Data & Paper Trading)
- Finnhub / AlphaVantage / NewsAPI (For News Aggregation)

**3. Run the Bot (Simulation Mode)**
To see the bot analyze today's market without risking real capital:
```bash
python main2.py
```

**4. Train the AI (Historical Learning)**
To force the bot to run through a historical simulation and train its XGBoost model:
```bash
python run_legendary_sim.py
```

---
*Built to eliminate human emotion from the market. Ruthless execution. Continuous adaptation.*
