from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
import asyncio
import os
import json
from datetime import datetime

from config import MODE, LOG_LEVEL, RUN_INTERVAL_SECONDS
from src.api.alpaca import get_alpaca_client
from config import ALPACA_CONFIG
from src.utils import logger
from src.utils.developer_log import dev_log
from src.notifications import notifier
from main2 import trading_bot, kb, news_agg, trend_analyzer, strategy_researcher
import main2  # Import module to access/modify globals like AI_REASONING_MODE
from src.scalper import Scalper
from src.simulation_engine import SimulatorEngine

app = Flask(__name__)
# Security: Load SECRET_KEY from environment variable
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
if not os.environ.get('SECRET_KEY'):
    logger.warning('SECRET_KEY not set in environment! Using random key (sessions will not persist across restarts)')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize Alpaca Client (aliased as robinhood for compatibility)
robinhood = get_alpaca_client(
    api_key=ALPACA_CONFIG.get('api_key'),
    secret_key=ALPACA_CONFIG.get('secret_key'),
    paper=ALPACA_CONFIG.get('paper', True)
)

# Global state
bot_thread = None
bot_running = False
bot_mode = MODE
stop_bot_flag = False

# Initialize Scalper
scalper_bot = Scalper()

# Bot Controller
class BotController:
    """
    Controls the execution state of the trading bot.
    Manages starting, stopping, and checking the running status.
    """
    @property
    def running(self):
        return bot_running
        
    def start(self):
        """Starts the bot loop in a background thread."""
        start_bot_loop()
        
    def stop(self):
        """Signals the bot loop to stop securely."""
        global stop_bot_flag
        stop_bot_flag = True

bot_controller = BotController()

# Custom logger that emits to WebSocket - DISABLED FOR PRIVATE LOGGING
# class WebSocketLogger:
#     def __init__(self):
#         self.original_log = logger.log
#         logger.log = self.log
#     
#     def log(self, level, msg):
#         # Call original logger
#         self.original_log(level, msg)
#         # Emit to WebSocket
#         try:
#             socketio.emit('log_message', {
#                 'message': msg,
#                 'level': level.lower(),
#                 'timestamp': datetime.now().isoformat()
#             })
#         except:
#             pass

# Initialize WebSocket logger
# ws_logger = WebSocketLogger()

@app.route('/')
def index():
    return render_template('index_v2.html')

@app.route('/health')
def health():
    """Health check endpoint for load balancers"""
    from src.utils.health import health_check
    from flask import jsonify
    
    health_status = health_check.check_all()
    status_code = 200 if health_status['status'] in ['healthy', 'degraded'] else 503
    
    return jsonify(health_status), status_code

@app.route('/api/config/update_custom_bot', methods=['POST'])
def update_custom_bot():
    """Update Custom Bot configuration"""
    try:
        from src.config_manager import config_manager
        data = request.json
        symbols = data.get('symbols', [])
        
        # Validate symbols (basic check)
        if not symbols or not isinstance(symbols, list):
             return jsonify({'status': 'error', 'message': 'Invalid symbol list'}), 400

        # Update config
        config_manager.update_bot_config('Custom', {'symbols': symbols})
        
        return jsonify({'status': 'success', 'message': f'Custom Bot updated to trade: {symbols}'})
    except Exception as e:
        logger.error(f"Error updating custom bot: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Scalping Bot Endpoints
@app.route('/api/scalping/status')
def scalping_status():
    return jsonify(scalper_bot.get_status())

@app.route('/api/scalping/start', methods=['POST'])
def start_scalping():
    try:
        scalper_bot.start_scalping()
        return jsonify({'status': 'success', 'message': 'Scalping bot started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/scalping/stop', methods=['POST'])
def stop_scalping():
    try:
        scalper_bot.stop_scalping()
        return jsonify({'status': 'success', 'message': 'Scalping bot stopped'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/scalping/config', methods=['POST'])
def update_scalping_config():
    try:
        data = request.json
        scalper_bot.update_config(
            min_vol=data.get('min_volatility'),
            tp=data.get('take_profit'),
            sl=data.get('stop_loss')
        )
        return jsonify({'status': 'success', 'message': 'Scalping config updated'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected to GUI')
    emit('log_message', {
        'message': 'Connected to trading bot', 
        'level': 'success',
        'details': {
            'mode': MODE,
            'log_level': LOG_LEVEL,
            'alpaca_paper': ALPACA_CONFIG.get('paper'),
            'run_interval': RUN_INTERVAL_SECONDS
        }
    })
    emit('bot_status', {
        'running': bot_controller.running,
        'mode': bot_mode,
        'reasoning_mode': getattr(main2, 'AI_REASONING_MODE', 'basic')
    })



@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected from GUI')

@socketio.on('start_bot')
def handle_start_bot(data):
    global bot_mode, stop_bot_flag
    
    # Validate input
    from src.utils.validators import StartBotSchema, sanitize_input
    from marshmallow import ValidationError
    
    try:
        validated_data = sanitize_input(data, StartBotSchema())
    except ValidationError as e:
        emit('log_message', {
            'message': f'Invalid input: {str(e)}',
            'level': 'error'
        })
        return
    
    if bot_controller.running:
        emit('log_message', {
            'message': 'Bot is already running',
            'level': 'warning'
        })
        return
    
    bot_mode = validated_data['mode']
    stop_bot_flag = False
    
    # Update config mode
    import config
    config.MODE = bot_mode
    
    logger.info(f'Starting bot in {bot_mode} mode...')
    
    # Start bot controller
    try:
        bot_controller.start()
        
        emit('bot_status', {
            'running': True,
            'mode': bot_mode,
            'reasoning_mode': getattr(main2, 'AI_REASONING_MODE', 'basic')
        }, broadcast=True)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        emit('log_message', {'level': 'error', 'message': f'Start failed: {e}'})

@socketio.on('stop_bot')
def handle_stop_bot():
    global stop_bot_flag
    
    if not bot_controller.running:
        emit('log_message', {
            'message': 'Bot is not running',
            'level': 'warning'
        })
        return
    
    logger.info('Stopping bot...')
    stop_bot_flag = True
    
    try:
        bot_controller.stop()
        
        emit('bot_status', {
            'running': False,
            'mode': bot_mode,
            'reasoning_mode': getattr(main2, 'AI_REASONING_MODE', 'basic')
        }, broadcast=True)
        
    except Exception as e:
         logger.error(f"Error stopping bot: {e}")

@socketio.on('set_reasoning_mode')
def handle_set_reasoning_mode(data):
    """Handle changing the AI reasoning mode (Basic vs Advanced)"""
    new_mode = data.get('mode')
    if new_mode in ['basic', 'advanced']:
        # Update the global variable in main2 module
        main2.AI_REASONING_MODE = new_mode
        logger.info(f"🧠 AI Reasoning Mode set to: {new_mode.upper()}")
        
        emit('log_message', {
            'message': f'AI Mode changed to: {new_mode.upper()}',
            'level': 'success'
        }, broadcast=True)
        
        # Broadcast update to all clients
        emit('bot_status', {
            'running': bot_running,
            'mode': bot_mode,
            'reasoning_mode': new_mode
        }, broadcast=True)
    else:
        emit('log_message', {
            'message': f'Invalid AI mode: {new_mode}',
            'level': 'error'
        })

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
            except Exception as e:
                logger.warning(f"Error calculating approximate price for {pos['symbol']}: {e}")
                price = cost_basis / qty if qty > 0 else 0
                
            value = qty * price
            # portfolio_value += value  <-- Don't manually sum, use API equity
            total_pl += (value - cost_basis)
        
        # Use authoritative values from broker API
        # Map 'portfolio_value' (Equity in App.js) to 'portfolio_equity' from API
        api_equity = float(account_info.get('portfolio_equity', 0))
        api_cash = float(account_info.get('portfolio_cash', 0))
        
        logger.info(f"💰 STATUS: Equity=${api_equity}, Cash=${api_cash}, Positions={len(portfolio_stocks)+len(crypto_positions)}")
        
        emit('status_update', {
            'portfolio_value': api_equity, # App.js treats this as Equity (Positions Value)
            'buying_power': api_cash,      # App.js adds this to portfolio_value to get Balance. Sending CASH here for correct Balance.
            'total_pl': total_pl
        })
        
        # Detailed log for activity feed
        emit('log_message', {
            'message': 'Account Status Updated',
            'level': 'info',
            'details': {
                'equity': api_equity,
                'cash': api_cash,
                'positions_count': len(portfolio_stocks) + len(crypto_positions),
                'total_pl': total_pl,
                'stocks': list(portfolio_stocks.keys()),
                'crypto': [p['symbol'] for p in crypto_positions]
            }
        })
    except Exception as e:
        logger.error(f'Error getting status: {e}')
        emit('log_message', {'level': 'error', 'message': f'Failed to fetch status: {str(e)}'})

@app.route('/api/status/data', methods=['GET'])
def get_status_http():
    """Fallback HTTP endpoint for status data"""
    try:
        if not robinhood:
             return jsonify({'error': 'Not connected'}), 503
             
        account_info = robinhood.get_account_info()
        portfolio_stocks = robinhood.get_portfolio_stocks()
        crypto_positions = robinhood.get_crypto_positions()
        
        portfolio_value = 0
        total_pl = 0
        
        # Calculate PL from positions (for consistency with previous logic's side effects if any)
        # But for values we use API authority
        for symbol, stock in portfolio_stocks.items():
            value = float(stock['price']) * float(stock['quantity'])
            cost = float(stock['average_buy_price']) * float(stock['quantity'])
            total_pl += (value - cost)
            
        for pos in crypto_positions:
             qty = float(pos['quantity'])
             cost_basis = float(pos.get('cost_basis', {}).get('amount', 0))
             # Approximate price if needed or just use cost/qty
             value = qty * (cost_basis/qty if qty>0 else 0) 
             total_pl += (value - cost_basis)

        api_equity = float(account_info.get('portfolio_equity', 0))
        api_cash = float(account_info.get('portfolio_cash', 0))
        
        return jsonify({
            'portfolio_value': api_equity,
            'buying_power': api_cash,
            'total_pl': total_pl
        })
    except Exception as e:
        logger.error(f"HTTP Status Error: {e}")
        return jsonify({'error': str(e)}), 500

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
            except Exception as e:
                logger.warning(f"Error fetching crypto quote for {pos['symbol']}: {e}")
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
        emit('log_message', {'level': 'error', 'message': f'Failed to fetch portfolio: {str(e)}'})

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

@app.route('/api/strategy/history')
def get_strategy_history():
    """Get strategy decision history from DB"""
    try:
        # We use the strategy_weights table as a history of changes
        from src.data.db import db
        conn = db._get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM strategy_weights ORDER BY timestamp DESC LIMIT 50")
        rows = c.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            r = dict(row)
            # Reconstruct format expected by UI if possible, or adapt
            # UI expects: date, action, reason, weights
            history.append({
                "date": r['timestamp'],
                "action": "updated", # We only store updates
                "reason": r['reason'],
                "weights": json.loads(r['weights_json'])
            })
            
        return {'history': history}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/research/force', methods=['POST'])
def force_research():
    """Manually trigger research with selected sources"""
    from flask import request
    from src.utils.validators import ForceResearchSchema, sanitize_input
    from marshmallow import ValidationError
    
    try:
        # Validate input
        try:
            validated_data = sanitize_input(request.json or {}, ForceResearchSchema())
        except ValidationError as e:
            return {'error': f'Invalid input: {str(e)}'}, 400
        
        sources = validated_data['sources']
        
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
        
        def send_progress(text, percent, status='in-progress'):
            """Helper to emit research log events"""
            socketio.emit('research_log', {
                'type': 'progress',
                'message': text,
                'percent': percent,
                'status': status
            })
            time.sleep(0.1) # throttling for UI smoothness

        send_progress('Starting research cycle...', 0, 'in-progress')
        
        # Pass callback to fetch_all_news
        articles = news_agg.fetch_all_news(force_refresh=True, progress_callback=send_progress)
        
        logger.info(f"✅ Collected {len(articles)} articles")
        send_progress(f'Collected {len(articles)} articles', 100, 'success')
        
        # Log individual articles
        for i, article in enumerate(articles):
            socketio.emit('research_log', {
                'type': 'article',
                'title': article.get('title', 'No Title'),
                'source': article.get('source_name', 'Unknown'),
                'summary': article.get('description') or article.get('summary') or 'No summary available',
                'url': article.get('url'),
                'index': i + 1,
                'total': len(articles)
            })
            if i >= 49: # Limit detailed logs to first 50 to avoid flooding
                socketio.emit('research_log', {'type': 'info', 'message': f'...and {len(articles)-50} more articles'})
                break
            time.sleep(0.05) # Slight delay for visual effect
        
        # Detect trends
        logger.info("🔎 Analyzing for trends...")
        socketio.emit('research_log', {'type': 'info', 'message': 'Analyzing for emerging trends...'})
        trends = trend_analyzer.detect_emerging_trends(min_articles=3)
        logger.info(f"📊 Detected {len(trends)} trends")
        
        for trend in trends:
            socketio.emit('research_log', {
                'type': 'trend',
                'name': trend['name'],
                'count': trend['article_count'],
                'trend_type': trend['type']
            })
        
        # Extract insights
        logger.info("🧠 Extracting insights...")
        socketio.emit('research_log', {'type': 'info', 'message': 'Extracting AI insights...'})
        insights = trend_analyzer.extract_insights_from_news(max_articles=15)
        logger.info(f"💡 Extracted {len(insights)} insights")
        
        for insight in insights:
            socketio.emit('research_log', {
                'type': 'insight',
                'text': insight['text'],
                'confidence': insight['metadata'].get('confidence', 0)
            })
        
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

@app.route('/api/day-trading/panic', methods=['POST'])
def panic_sell():
    """Panic sell all positions"""
    try:
        result = robinhood.close_all_positions()
        if result.get('status') == 'success':
            logger.warning("🚨 PANIC SELL TRIGGERED: All positions closed")
            return jsonify({'success': True, 'message': 'All positions closed'})
        else:
            return jsonify({'success': False, 'message': result.get('message')}), 500
    except Exception as e:
        logger.error(f"Panic sell error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
    
    # Bypass login for testing/paper mode
    robinhood_token_expiry = time.time() + 1000000 
    
    while bot_running and not stop_bot_flag:
        try:
            # Emit status to GUI
            socketio.emit('log_message', {
                'message': 'Bot loop starting...',
                'level': 'info'
            })
            
            # Check if Alpaca token needs refresh (Mocked)
            if time.time() >= robinhood_token_expiry - 300:
                socketio.emit('log_message', {
                    'message': 'Checking Alpaca connection...',
                    'level': 'info'
                })
                # logger.info("Checking Alpaca connection...")
                
                # Run async login in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                login_resp = loop.run_until_complete(robinhood.login_to_robinhood())
                loop.close()
                
                if not login_resp or 'expires_in' not in login_resp:
                    raise Exception("Failed to connect to Alpaca")
                robinhood_token_expiry = time.time() + login_resp['expires_in']
                
                socketio.emit('log_message', {
                    'message': f'✅ Alpaca connection successful! Session valid for {login_resp["expires_in"]}s',
                    'level': 'success'
                })
            
            # Allow running if market is open OR if we are in demo mode OR if Crypto is enabled
            from src.config_manager import config_manager
            metrics_config = config_manager.get_metrics()
            # Check for any enabled crypto bot
            crypto_bots = metrics_config.get('crypto_bots', [])
            crypto_enabled = metrics_config.get('crypto', {}).get('enabled', False) or any(b.get('enabled', False) for b in crypto_bots)
            
            logger.info(f"DEBUG LOOP CHECK: Market={robinhood.is_market_open()}, Mode={bot_mode}, CryptoEnabled={crypto_enabled}")
            
            if robinhood.is_market_open() or bot_mode == 'demo' or crypto_enabled:
                run_interval_seconds = RUN_INTERVAL_SECONDS
                logger.info(f"Running trading bot in {bot_mode} mode (Market Open: {robinhood.is_market_open()})...")
                
                # Define progress callback for detailed activity log
                def report_progress(text, percent, status='in-progress'):
                    # Emit step
                    socketio.emit('activity_step', {'text': text, 'status': status})
                    # Update progress
                    socketio.emit('activity_progress', {'percent': percent})
                
                # Define event callback for transparency
                def emit_decision_event(event_type, data):
                    socketio.emit('decision_update', {
                        'type': event_type,
                        'data': data,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Emit activity start
                socketio.emit('activity_start', {
                    'title': 'Trading Cycle Started',
                    'icon': '🔄',
                    'type': 'info'
                })
                
                # Initial steps
                report_progress('Checking market status...', 5, 'done')
                report_progress('Fetching account information...', 10, 'done')

                # Run trading bot with callbacks
                trading_results = trading_bot(
                    event_callback=emit_decision_event,
                    progress_callback=report_progress
                )
                
                # Complete activity
                socketio.emit('activity_progress', {'percent': 100})
                socketio.emit('activity_complete', {'success': True})
                
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
            except Exception as inner_e:
                logger.error(f"CRITICAL: Error inside crash handler: {inner_e}")
        
        # Wait with ability to stop
        for _ in range(run_interval_seconds):
            if stop_bot_flag:
                break
            time.sleep(1)
    
    bot_running = False
    logger.info("Bot stopped")


# -----------------------------------------------------------------------------
# WATCHLIST & ALERTS API
# -----------------------------------------------------------------------------
from src.alert_manager import alert_manager
from flask import request

@app.route('/api/log_client_event', methods=['POST'])
def log_client_event():
    """Receive and log events from the frontend for debugging"""
    try:
        data = request.json
        event_type = data.get('type', 'unknown')
        details = data.get('details', {})
        
        # Log to Persistent Dev Log
        dev_log.log_client_event(event_type, details)
        
        # Also keep console log
        logger.debug(f"🖱️ CLIENT_EVENT [{event_type}]: {details}")
        return jsonify({'status': 'logged'}), 200
    except Exception as e:
        logger.error(f"Error logging client event: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/developer/log', methods=['GET'])
def get_developer_log():
    """Get merged developer journey log"""
    try:
        logs = dev_log.get_full_log()
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/comparison', methods=['GET'])
def get_comparison_logs():
    """Get comparison logs from CSV"""
    try:
        log_file = "data/comparison_log.csv"
        if not os.path.exists(log_file):
            return {'logs': []}
        
        logs = []
        import csv
        # Use a safe read approach
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    logs.append(row)
        except Exception as read_err:
             logger.error(f"Error reading CSV: {read_err}")
             return {'logs': []}
        
        # Return newest first
        return {'logs': logs[::-1]}
    except Exception as e:
        logger.error(f"Error fetching comparison logs: {e}")
        return {'error': str(e)}, 500

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """Get current watchlist and alerts"""
    watchlist_symbols = alert_manager.get_watchlist() # This returns a list of symbols (strings)
    alerts = alert_manager.get_alerts()
    
    # Batch fetch data for all symbols
    # This optimizes API usage (1 call vs N calls) allowing faster refresh
    from src.data.intraday_data import intraday_data
    
    full_details = []
    
    try:
        # Pass the list of symbols directly
        batch_data = intraday_data.get_latest_data_batch(watchlist_symbols)
    except Exception as e:
        logger.error(f"Batch fetch failed: {e}")
        batch_data = {}

    for sym in watchlist_symbols: # Iterate over the symbols directly
        
        # Default values
        current_price = 0.0
        pct_change = 0.0
        
        # Get data from batch result
        df = batch_data.get(sym)
        
        if df is not None and not df.empty:
            current_price = df['Close'].iloc[-1]
            # Calculate change from previous close (if available)
            if len(df) >= 2:
                prev_close = df['Close'].iloc[-2]
                if prev_close != 0: # Avoid division by zero
                    pct_change = ((current_price - prev_close) / prev_close) * 100
                
            # Update cache/storage with latest price (if alert_manager supports this)
            # alert_manager.update_watchlist_price(sym, current_price, pct_change) # This function doesn't exist in alert_manager in the provided context, commenting out.
            
        full_details.append({
            'symbol': sym,
            'price': current_price,
            'change': pct_change
        })
        
    return {
        'watchlist': full_details, # Use full_details here
        'alerts': alerts
    }

@app.route('/api/watchlist/add', methods=['POST'])
def add_to_watchlist():
    data = request.json
    symbol = data.get('symbol')
    if symbol:
        if alert_manager.add_to_watchlist(symbol):
            return {'success': True, 'message': f'Added {symbol}'}
        return {'success': False, 'message': 'Already in watchlist'}
    return {'error': 'Symbol required'}, 400

@app.route('/api/watchlist/remove', methods=['POST'])
def remove_from_watchlist():
    data = request.json
    symbol = data.get('symbol')
    if symbol:
        if alert_manager.remove_from_watchlist(symbol):
            return {'success': True, 'message': f'Removed {symbol}'}
        return {'success': False, 'message': 'Not in watchlist'}
    return {'error': 'Symbol required'}, 400

@app.route('/api/alerts/create', methods=['POST'])
def create_alert():
    data = request.json
    symbol = data.get('symbol')
    condition = data.get('condition')
    value = data.get('value')
    
    if symbol and condition and value is not None:
        alert = alert_manager.create_alert(symbol, condition, float(value))
        return {'success': True, 'alert': alert}
    return {'error': 'Missing fields'}, 400

@app.route('/api/alerts/delete', methods=['POST'])
def delete_alert():
    data = request.json
    alert_id = data.get('alert_id')
    if alert_id:
        if alert_manager.delete_alert(int(alert_id)):
            return {'success': True}
        return {'success': False, 'message': 'Alert not found'}
    return {'error': 'Alert ID required'}, 400

@app.route('/api/debug_log', methods=['GET'])
def debug_log():
    msg = request.args.get('msg', 'No message')
    logger.info(f"CLIENT DEBUG: {msg}")
    return jsonify({'status': 'ok'})

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current strategy configuration"""
    from src.config_manager import config_manager
    return jsonify({'config': config_manager.get_metrics()})

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get trading history"""
    try:
        if os.path.exists('data/overnight_trades.json'):
            with open('data/overnight_trades.json', 'r') as f:
                trades = json.load(f)
            # Sort by timestamp desc
            trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return jsonify({'trades': trades})
        return jsonify({'trades': []})
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulate', methods=['POST'])
def run_simulation():
    try:
        data = request.json
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_cash = float(data.get('initial_cash', 10000))
        universe_str = data.get('universe', '')
        universe = [s.strip().upper() for s in universe_str.split(',') if s.strip()]
        
        if not universe:
            return jsonify({'error': 'No stocks selected'}), 400
            
        logger.info(f"Received Simulation Request: {universe} from {start_date} to {end_date}")
        
        # Instantiate and run
        sim = SimulatorEngine(start_date, end_date, initial_cash, universe)
        results = sim.run()
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/update', methods=['POST'])
def update_config():
    """Update strategy configuration"""
    from src.config_manager import config_manager
    try:
        new_config = request.json
        config_manager.update_metrics(new_config)
        return jsonify({'status': 'success', 'config': config_manager.get_metrics()})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

def start_bot_loop():
    """Helper to start the bot loop thread"""
    global bot_thread, bot_running, bot_mode, stop_bot_flag
    
    if bot_running:
        return

    bot_running = True
    stop_bot_flag = False
    
    logger.info(f'Starting bot in {bot_mode} mode...')
    
    bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
    bot_thread.start()

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Robinhood AI Trading Bot - Web GUI V2")
    print("=" * 60)
    print(f"Opening GUI at: http://localhost:5004")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Start the bot loop in a separate thread
    start_bot_loop()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5004))
    logger.info(f"🚀 Starting GUI server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
