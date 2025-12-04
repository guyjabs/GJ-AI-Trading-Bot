# GJ AI Trading Bot

AI-powered trading bot using Alpaca for commission-free stock and cryptocurrency trading.

## 🚀 Features

- 🤖 **AI-Driven Decisions** - GPT-4 powered trading strategy
- 📊 **Real-Time Analysis** - Live market data and technical indicators
- 📰 **News Sentiment** - Automated news aggregation and sentiment analysis
- 💹 **Stocks + Crypto** - Trade both stocks and cryptocurrencies
- 📈 **Paper Trading** - Test strategies with fake money
- 🎯 **Risk Management** - Built-in safety limits and position sizing
- 🔬 **Research Bot** - Continuous market research and strategy optimization

## 📋 Prerequisites

- Python 3.10+
- [Alpaca](https://alpaca.markets) account (free paper trading available)
- OpenAI API key
- (Optional) NewsAPI, Alpha Vantage, Finnhub API keys for enhanced research

## ⚡ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/guyjabs/GJ-AI-Trading-Bot.git
cd "GJ AI Trading Bot"
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Alpaca API Keys

1. Sign up at [alpaca.markets](https://alpaca.markets)
2. Go to Paper Trading section
3. Generate API keys
4. Copy both API Key ID and Secret Key

### 5. Configure the Bot

```bash
cp config.py.example config.py
```

Edit `config.py` and add your credentials:

```python
# Alpaca API Credentials
ALPACA_CONFIG = {
    'api_key': 'YOUR_API_KEY_HERE',
    'secret_key': 'YOUR_SECRET_KEY_HERE',
    'paper': True,  # Keep True for paper trading
}

# OpenAI API Key
OPENAI_API_KEY = "your-openai-api-key"
```

### 6. Run the Bot

```bash
python main.py
```

## 🎮 Trading Modes

- **demo** - Paper trading with AI decisions (safe for testing)
- **auto** - Automated live trading (requires live Alpaca account)
- **manual** - AI suggestions only, you approve trades

Set mode in `config.py`:

```python
MODE = "demo"  # Start with demo mode
```

## 📊 Supported Assets

### Stocks
- All US stocks available on Alpaca
- Fractional shares supported
- Market hours: 9:30 AM - 4:00 PM ET

### Cryptocurrencies
- BTC/USD, ETH/USD, LTC/USD, BCH/USD
- AAVE/USD, UNI/USD, LINK/USD
- 24/7 trading
- Commission-free

## 🔧 Configuration

Key settings in `config.py`:

```python
# Trading Parameters
PORTFOLIO_LIMIT = 10  # Max number of positions
MIN_BUYING_AMOUNT_USD = 1.0  # Minimum trade size
MAX_BUYING_AMOUNT_USD = 10.0  # Maximum trade size
MIN_BUYING_POWER_BUFFER = 50.0  # Keep $50 cash buffer

# AI Model
OPENAI_MODEL_NAME = "gpt-4o-mini"  # Or "gpt-4" for better decisions

# Research Bot
ENABLE_RESEARCH_BOT = True  # Enable continuous market research
NEWS_FETCH_INTERVAL_HOURS = 1  # How often to fetch news
```

## 🧪 Testing

Always start with paper trading:

```python
ALPACA_CONFIG = {
    'paper': True,  # Paper trading (fake money)
}
MODE = "demo"  # Demo mode
```

Monitor the bot for several days before considering live trading.

## 📈 How It Works

1. **Market Analysis** - Fetches real-time market data and news
2. **AI Decision** - GPT-4 analyzes data and suggests trades
3. **Risk Check** - Validates against safety limits
4. **Execute** - Places orders via Alpaca API
5. **Monitor** - Tracks positions and adjusts strategy

## 🛡️ Safety Features

- **Paper Trading** - Test without risk
- **Position Limits** - Max portfolio size
- **Cash Buffer** - Never spend last dollar
- **Trade Size Limits** - Min/max per trade
- **AI Validation** - Double-check decisions

## 📚 Documentation

- [Alpaca API Docs](https://docs.alpaca.markets/)
- [OpenAI API Docs](https://platform.openai.com/docs)

## ⚠️ Disclaimer

**This bot is for educational purposes only. Trading involves risk of loss. Never invest more than you can afford to lose. Past performance does not guarantee future results. Use at your own risk.**

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 💬 Support

For issues or questions, please open a GitHub issue.

---

**Made with ❤️ by Guy Jaber**
