from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import time
import asyncio
from datetime import datetime

from config import MODE, LOG_LEVEL, RUN_INTERVAL_SECONDS
from src.api import robinhood
from src.utils import logger
from src.notifications import notifier
from main import trading_bot, kb, news_agg, trend_analyzer, strategy_researcher

app = Flask(__name__)
app.config['SECRET_KEY'] = 'robinhood-ai-trading-bot-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
bot_thread = None
bot_running = False
bot_mode = MODE
stop_bot_flag = False

# Custom logger that emits to WebSocket
class WebSocketLogger:
    def __init__(self):
        self.original_log = logger.log
        logger.log = self.log
    
    def log(self, level, msg):
        # Call original logger
        self.original_log(level, msg)
        # Emit to WebSocket
        try:
            socketio.emit('log_message', {
                'message': msg,
                'level': level.lower(),
                'timestamp': datetime.now().isoformat()
            })
        except:
            pass

# Initialize WebSocket logger
ws_logger = WebSocketLogger()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected to GUI')
    emit('bot_status', {
        'running': bot_running,
        'mode': bot_mode
    })

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected from GUI')

@socketio.on('start_bot')
def handle_start_bot(data):
    global bot_thread, bot_running, bot_mode, stop_bot_flag
    
    if bot_running:
        emit('log_message', {
            'message': 'Bot is already running',
            'level': 'warning'
        })
        return
    
    bot_mode = data.get('mode', 'demo')
    stop_bot_flag = False
    bot_running = True
    
    # Update config mode
    import config
    config.MODE = bot_mode
    
    logger.info(f'Starting bot in {bot_mode} mode...')
    
    # Start bot in background thread
    bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
    bot_thread.start()
    
    emit('bot_status', {
        'running': True,
        'mode': bot_mode
    }, broadcast=True)

@socketio.on('stop_bot')
def handle_stop_bot():
    global bot_running, stop_bot_flag
    
    if not bot_running:
        emit('log_message', {
            'message': 'Bot is not running',
            'level': 'warning'
        })
        return
    
    logger.info('Stopping bot...')
    stop_bot_flag = True
    bot_running = False
    
    emit('bot_status', {
        'running': False,
        'mode': bot_mode
    }, broadcast=True)

@socketio.on('get_status')
def handle_get_status():
    try:
        account_info = robinhood.get_account_info()
        portfolio_stocks = robinhood.get_portfolio_stocks()
        crypto_positions = robinhood.get_crypto_positions()
        
        portfolio_value = 0
        total_pl = 0
        
        # Stocks
        for symbol, stock in portfolio_stocks.items():
            value = float(stock['price']) * float(stock['quantity'])
            portfolio_value += value
            cost = float(stock['average_buy_price']) * float(stock['quantity'])
            total_pl += (value - cost)
            
        # Crypto
        for pos in crypto_positions:
            qty = float(pos['quantity'])
            cost_basis = float(pos['cost_basis']['amount'])
            
            # Get current price (approximate from cost basis if quote fails to save API calls)
            # For status update, we might want real price
            try:
                quote = robinhood.get_crypto_quote(pos['symbol'])
                price = float(quote['mark_price'])
            except:
                price = cost_basis / qty if qty > 0 else 0
                
            value = qty * price
            portfolio_value += value
            total_pl += (value - cost_basis)
        
        emit('status_update', {
            'portfolio_value': portfolio_value,
            'buying_power': float(account_info['buying_power']),
            'total_pl': total_pl
        })
    except Exception as e:
        logger.error(f'Error getting status: {e}')

@socketio.on('get_portfolio')
def handle_get_portfolio():
    try:
        portfolio_stocks = robinhood.get_portfolio_stocks()
        crypto_positions = robinhood.get_crypto_positions()
        
        portfolio = []
        
        # Stocks
        for symbol, stock in portfolio_stocks.items():
            portfolio.append({
                'symbol': symbol,
                'quantity': float(stock['quantity']),
                'current_price': float(stock['price']),
                'average_buy_price': float(stock['average_buy_price']),
                'type': 'stock'
            })
            
        # Crypto
        for pos in crypto_positions:
            qty = float(pos['quantity'])
            cost_basis = float(pos['cost_basis']['amount'])
            avg_price = cost_basis / qty if qty > 0 else 0
            
            try:
                quote = robinhood.get_crypto_quote(pos['symbol'])
                price = float(quote['mark_price'])
            except:
                price = avg_price
                
            portfolio.append({
                'symbol': pos['symbol'],
                'quantity': qty,
                'current_price': price,
                'average_buy_price': avg_price,
                'type': 'crypto'
            })
        
        emit('portfolio_update', {
            'portfolio': portfolio
        })
    except Exception as e:
        logger.error(f'Error getting portfolio: {e}')

@app.route('/api/research/news')
def get_research_news():
    try:
        articles = news_agg.fetch_all_news(use_cache=True)
        return {'articles': articles[:50]} # Limit to 50
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/research/trends')
def get_research_trends():
    try:
        trends = kb.get_recent_trends(limit=20)
        return {'trends': trends}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/research/predictions')
def get_research_predictions():
    try:
        predictions = kb.get_active_predictions()
        return {'predictions': predictions}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/research/summary')
def get_research_summary():
    try:
        summary = trend_analyzer.generate_market_summary()
        return summary
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/research/force', methods=['POST'])
def force_research():
    """Manually trigger research with selected sources"""
    try:
        data = request.json
        sources = data.get('sources', {})
        
        logger.info("🚀 Manual research triggered by user")
        logger.info(f"📋 Selected sources: {', '.join([k for k, v in sources.items() if v])}")
        
        # Temporarily modify news aggregator to use only selected sources
        original_keys = {
            'newsapi': news_agg.newsapi_key,
            'alphavantage': news_agg.alphavantage_key,
            'finnhub': news_agg.finnhub_key
        }
        
        # Disable unchecked sources
        if not sources.get('newsapi', False):
            news_agg.newsapi_key = None
        if not sources.get('alphavantage', False):
            news_agg.alphavantage_key = None
        if not sources.get('finnhub', False):
            news_agg.finnhub_key = None
        
        # Run research
        logger.info("🔍 Starting manual research cycle...")
        articles = news_agg.fetch_all_news(force_refresh=True)
        logger.info(f"✅ Collected {len(articles)} articles")
        
        # Detect trends
        logger.info("🔎 Analyzing for trends...")
        trends = trend_analyzer.detect_emerging_trends(min_articles=3)
        logger.info(f"📊 Detected {len(trends)} trends")
        
        # Extract insights
        logger.info("🧠 Extracting insights...")
        insights = trend_analyzer.extract_insights_from_news(max_articles=15)
        logger.info(f"💡 Extracted {len(insights)} insights")
        
        # Restore original keys
        news_agg.newsapi_key = original_keys['newsapi']
        news_agg.alphavantage_key = original_keys['alphavantage']
        news_agg.finnhub_key = original_keys['finnhub']
        
        logger.info("✅ Manual research complete!")
        
        return {
            'success': True,
            'articles_count': len(articles),
            'trends_count': len(trends),
            'insights_count': len(insights)
        }
        
    except Exception as e:
        logger.error(f"❌ Error in manual research: {e}")
        return {'error': str(e)}, 500

        return {'error': str(e)}, 500

@app.route('/api/day-trading/dashboard')
def get_day_trading_dashboard():
    """Get real-time data for Day Trading Dashboard"""
    try:
        from src.day_trading.day_screener import day_screener
        from src.day_trading.stop_loss_manager import stop_loss_manager
        from src.day_trading.profit_target_manager import profit_target_manager
        from src.day_trading.discretionary_filter import discretionary_filter
        from src.trade_journal import trade_journal
        
        # 1. Get Intraday Stats
        # In a real app, we'd calculate this from today's trades in journal
        trades_today = trade_journal.get_recent_trades(limit=50) # Filter for today in SQL
        # For now, mock or simple calc
        today_pnl = 0.0
        win_rate = "0%"
        trades_count = 0
        
        # 2. Get Active Day Trades
        # We need to track active day trades in memory or DB. 
        # For now, let's assume we get them from portfolio + managers
        portfolio = robinhood.get_portfolio_overview()
        active_trades = []
        
        for symbol, data in portfolio.items():
            # Only include if it has a stop loss (implies day trade)
            stop_price = stop_loss_manager.get_stop_price(symbol)
            if stop_price:
                current_price = float(data['price'])
                entry_price = float(data['average_buy_price'])
                target_price = profit_target_manager.active_targets.get(symbol, 0)
                
                pnl = (current_price - entry_price) * float(data['quantity'])
                risk = entry_price - stop_price
                r_multiple = (current_price - entry_price) / risk if risk > 0 else 0
                
                active_trades.append({
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'stop_loss': stop_price,
                    'target': target_price,
                    'pnl': pnl,
                    'r_multiple': r_multiple
                })
        
        # 3. Get Scanner Results
        # Run quick scan or get cached
        gappers = day_screener.scan_gappers()[:5]
        momentum = day_screener.scan_momentum()[:5]
        
        # 4. Get Market Context
        spy_trend = "Bullish" if discretionary_filter.check_market_alignment('long') else "Bearish"
        
        return {
            'pnl': today_pnl,
            'pnl_formatted': f"${today_pnl:.2f}",
            'trades_count': trades_count,
            'win_rate': win_rate,
            'market_context': {
                'spy_trend': spy_trend
            },
            'active_trades': active_trades,
            'scanner': {
                'gappers': [{'symbol': g['symbol'], 'detail': f"{g['gap_pct']:.2f}% Gap"} for g in gappers],
                'momentum': [{'symbol': m['symbol'], 'detail': f"RVOL {m['rvol']:.2f}"} for m in momentum]
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching day trading dashboard: {e}")
        return {'error': str(e)}, 500

def run_bot_loop():
    """Main bot loop running in background thread"""
    global bot_running, stop_bot_flag
    
    robinhood_token_expiry = 0
    
    while bot_running and not stop_bot_flag:
        try:
            # Emit status to GUI
            socketio.emit('log_message', {
                'message': 'Bot loop starting...',
                'level': 'info'
            })
            
            # Check if Robinhood token needs refresh
            if time.time() >= robinhood_token_expiry - 300:
                socketio.emit('log_message', {
                    'message': 'Attempting Robinhood login...',
                    'level': 'info'
                })
                logger.info("Login to Robinhood...")
                # Run async login in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                login_resp = loop.run_until_complete(robinhood.login_to_robinhood())
                loop.close()
                
                if not login_resp or 'expires_in' not in login_resp:
                    raise Exception("Failed to login to Robinhood")
                robinhood_token_expiry = time.time() + login_resp['expires_in']
                logger.info(f"Successfully logged in. Token expires in {login_resp['expires_in']} seconds")
                socketio.emit('log_message', {
                    'message': f'✅ Robinhood login successful! Token valid for {login_resp["expires_in"]}s',
                    'level': 'success'
                })
            
            if robinhood.is_market_open():
                run_interval_seconds = RUN_INTERVAL_SECONDS
                logger.info(f"Market is open, running trading bot in {bot_mode} mode...")
                
                # Run trading bot
                trading_results = trading_bot()
                
                # Emit trade results
                for symbol, result in trading_results.items():
                    socketio.emit('trade_executed', {
                        'symbol': symbol,
                        'decision': result['decision'],
                        'quantity': result['quantity'],
                        'result': result['result'],
                        'details': str(result['details'])
                    })
                
                # Update portfolio and status
                socketio.emit('get_portfolio')
                socketio.emit('get_status')
                
                # Log summary
                sold_stocks = [f"{result['symbol']} ({result['quantity']})" for result in trading_results.values() if result['decision'] == "sell" and result['result'] == "success"]
                bought_stocks = [f"{result['symbol']} ({result['quantity']})" for result in trading_results.values() if result['decision'] == "buy" and result['result'] == "success"]
                errors = [f"{result['symbol']} ({result['details']})" for result in trading_results.values() if result['result'] == "error"]
                
                logger.info(f"Sold: {'None' if len(sold_stocks) == 0 else ', '.join(sold_stocks)}")
                logger.info(f"Bought: {'None' if len(bought_stocks) == 0 else ', '.join(bought_stocks)}")
                logger.info(f"Errors: {'None' if len(errors) == 0 else ', '.join(errors)}")
            else:
                run_interval_seconds = 60
                logger.info("Market is closed, waiting for next run...")
        except Exception as e:
            run_interval_seconds = 60
            error_msg = f"Trading bot crashed (Watchdog recovering in 60s): {e}"
            logger.error(error_msg)
            try:
                notifier.notify_error(error_msg)
            except:
                pass # Don't crash the crash handler
        
        # Wait with ability to stop
        for _ in range(run_interval_seconds):
            if stop_bot_flag:
                break
            time.sleep(1)
    
    bot_running = False
    logger.info("Bot stopped")

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Robinhood AI Trading Bot - Web GUI")
    print("=" * 60)
    print(f"Opening GUI at: http://localhost:5001")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5001)
