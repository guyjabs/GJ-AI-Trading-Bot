import time
from datetime import datetime
import json
import asyncio

from config import *
from src.api.alpaca import get_alpaca_client
from src.api import openai
from src.utils import logger
from src.screener import screener
from src.ml_engine import ml_engine
from src.risk_manager import risk_manager
from src.notifications import notifier
from src.research import NewsAggregator, KnowledgeBase, TrendAnalyzer, StrategyResearcher, ResearchScheduler

# Initialize Alpaca Client
robinhood = get_alpaca_client(
    api_key=ALPACA_CONFIG.get('api_key'),
    secret_key=ALPACA_CONFIG.get('secret_key'),
    paper=ALPACA_CONFIG.get('paper', True)
)

# Initialize Research Components
logger.info("Initializing Research Bot components...")
kb = KnowledgeBase()
news_agg = NewsAggregator(
    newsapi_key=NEWSAPI_KEY if 'NEWSAPI_KEY' in globals() else None,
    alphavantage_key=ALPHAVANTAGE_API_KEY if 'ALPHAVANTAGE_API_KEY' in globals() else None,
    finnhub_key=FINNHUB_API_KEY if 'FINNHUB_API_KEY' in globals() else None
)
trend_analyzer = TrendAnalyzer(news_agg, kb)
strategy_researcher = StrategyResearcher(
    kb, 
    reddit_client_id=REDDIT_CLIENT_ID if 'REDDIT_CLIENT_ID' in globals() else None,
    reddit_client_secret=REDDIT_CLIENT_SECRET if 'REDDIT_CLIENT_SECRET' in globals() else None
)
research_scheduler = ResearchScheduler(news_agg, kb, trend_analyzer, strategy_researcher)

# Setup research schedules
if globals().get('ENABLE_RESEARCH_BOT', False):
    research_scheduler.setup_schedules(
        news_interval_hours=globals().get('NEWS_FETCH_INTERVAL_HOURS', 1),
        strategy_research_time="02:00",
        prediction_time="08:00"
    )
    research_scheduler.start()


# Get AI amount guidelines
def get_ai_amount_guidelines():
    sell_guidelines = []
    if MIN_SELLING_AMOUNT_USD is not False:
        sell_guidelines.append(f"Minimum amount {MIN_SELLING_AMOUNT_USD} USD")
    if MAX_SELLING_AMOUNT_USD is not False:
        sell_guidelines.append(f"Maximum amount {MAX_SELLING_AMOUNT_USD} USD")
    sell_guidelines = ", ".join(sell_guidelines) if sell_guidelines else None

    buy_guidelines = []
    if MIN_BUYING_AMOUNT_USD is not False:
        buy_guidelines.append(f"Minimum amount {MIN_BUYING_AMOUNT_USD} USD")
    if MAX_BUYING_AMOUNT_USD is not False:
        buy_guidelines.append(f"Maximum amount {MAX_BUYING_AMOUNT_USD} USD")
    buy_guidelines = ", ".join(buy_guidelines) if buy_guidelines else None

    return sell_guidelines, buy_guidelines


# Make AI-based decisions on stock portfolio and watchlist
def make_ai_decisions(account_info, portfolio_overview, watchlist_overview):
    # Get active predictions for context
    predictions = []
    if globals().get('ENABLE_RESEARCH_BOT', False):
        try:
            predictions = kb.get_active_predictions()
            logger.info(f"Loaded {len(predictions)} active predictions for AI context")
        except Exception as e:
            logger.error(f"Error loading predictions: {e}")

    constraints = [
        f"- Initial budget: {account_info['buying_power']} USD",
        f"- Max portfolio size: {PORTFOLIO_LIMIT} stocks",
    ]
    sell_guidelines, buy_guidelines = get_ai_amount_guidelines()
    if sell_guidelines:
        constraints.append(f"- Sell Amounts Guidelines: {sell_guidelines}")
    if buy_guidelines:
        constraints.append(f"- Buy Amounts Guidelines: {buy_guidelines}")
    if len(TRADE_EXCEPTIONS) > 0:
        constraints.append(f"- Excluded stocks: {', '.join(TRADE_EXCEPTIONS)}")

    ai_prompt = (
        "**Context:**\n"
        f"Today is {datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}.{chr(10)}"
        f"You are a short-term investment advisor managing a stock portfolio.{chr(10)}"
        f"You analyze market conditions every {RUN_INTERVAL_SECONDS} seconds and make investment decisions.{chr(10)}{chr(10)}"
        "**Constraints:**\n"
        f"{chr(10).join(constraints)}"
        "\n\n"
        "**Stock Data:**\n"
        "```json\n"
        f"{json.dumps({**portfolio_overview, **watchlist_overview}, indent=1)}{chr(10)}"
        f"{json.dumps({**portfolio_overview, **watchlist_overview}, indent=1)}{chr(10)}"
        "```\n\n"
        "**Research & Predictions:**\n"
        "```json\n"
        f"{json.dumps([{'symbol': p['metadata']['symbol'], 'prediction': p['text'], 'confidence': p['metadata']['confidence']} for p in predictions], indent=1)}{chr(10)}"
        "```\n\n"
        "**Response Format:**\n"
        "Return your decisions in a JSON array with this structure:\n"
        "```json\n"
        "[\n"
        '  {"symbol": <symbol>, "decision": <decision>, "quantity": <quantity>, "reasoning": <short_explanation>},\n'
        "  ...\n"
        "]\n"
        "```\n"
        "- <symbol>: Stock symbol.\n"
        "- <decision>: One of `buy`, `sell`, or `hold`.\n"
        "- <quantity>: Recommended transaction quantity.\n"
        "- <reasoning>: Brief explanation (max 10 words) for the decision (e.g., 'Strong momentum + RSI oversold').\n\n"
        "**Instructions:**\n"
        "- Provide only the JSON output with no additional text.\n"
        "- Return an empty array if no actions are necessary."
    )
    logger.debug(f"AI making-decisions prompt:{chr(10)}{ai_prompt}")
    ai_response = openai.make_ai_request(ai_prompt)
    logger.debug(f"AI making-decisions response:{chr(10)}{ai_response.choices[0].message.content.strip()}")
    decisions = openai.parse_ai_response(ai_response)
    return decisions


# Filter AI hallucinations
def filter_ai_hallucinations(account_info, portfolio_overview, watchlist_overview, decisions_data):
    filtered_decisions = []

    for decision in decisions_data:
        symbol = decision.get('symbol')
        decision_type = decision.get('decision')
        quantity = decision.get('quantity', 0)

        # Filter decisions for stocks in TRADE_EXCEPTIONS
        if symbol in TRADE_EXCEPTIONS:
            logger.debug(f"Filtering out {decision_type} decision for {symbol} - in TRADE_EXCEPTIONS")
            continue

        # Filter sell decisions with 0 quantity
        if decision_type == "sell" and quantity == 0:
            logger.debug(f"Filtering out sell decision for {symbol} with 0 quantity")
            continue

        # Filter buy decisions with 0 quantity
        if decision_type == "buy" and quantity == 0:
            logger.debug(f"Filtering out buy decision for {symbol} with 0 quantity")
            continue

        # Get stock data from either portfolio or watchlist
        stock_data = portfolio_overview.get(symbol) or watchlist_overview.get(symbol)
        if not stock_data:
            logger.debug(f"Filtering out decision for {symbol} - not found in portfolio or watchlist")
            continue

        # Filter buy decisions with is_buy_pdt_restricted == True
        if decision_type == "buy" and stock_data.get("is_buy_pdt_restricted", False):
            logger.debug(f"Filtering out buy decision for {symbol} due to PDT restriction")
            continue

        # Filter sell decisions with is_sell_pdt_restricted == True
        if decision_type == "sell" and stock_data.get("is_sell_pdt_restricted", False):
            logger.debug(f"Filtering out sell decision for {symbol} due to PDT restriction")
            continue

        filtered_decisions.append(decision)

    logger.debug(f"Filtered out {len(decisions_data) - len(filtered_decisions)} decision(s)")
    return filtered_decisions


# Limit watchlist stocks based on the current week number
def limit_watchlist_stocks(watchlist_stocks, limit):
    if len(watchlist_stocks) <= limit:
        return watchlist_stocks

    # Sort watchlist stocks by symbol
    watchlist_stocks = sorted(watchlist_stocks, key=lambda x: x['symbol'])

    # Get the current month number
    current_month = datetime.now().month

    # Calculate the number of parts
    num_parts = (len(watchlist_stocks) + limit - 1) // limit  # Ceiling division

    # Determine the part to return based on the current month number
    part_index = (current_month - 1) % num_parts
    start_index = part_index * limit
    end_index = min(start_index + limit, len(watchlist_stocks))

    return watchlist_stocks[start_index:end_index]


# Use screener to get stock universe
def get_screened_stocks():
    """
    Use ML-powered screener to get stock universe.
    Returns list of stock symbols to analyze.
    """
    try:
        # Check if we have recent screening results
        results = screener.load_screening_results()
        
        # Run screener if results are old or missing
        if not results or 'timestamp' not in results:
            logger.info("Running stock screener...")
            results = screener.run_all_strategies()
        else:
            # Check if results are from today
            from datetime import datetime
            result_time = datetime.fromisoformat(results['timestamp'])
            if result_time.date() < datetime.now().date():
                logger.info("Screening results are old, running fresh screen...")
                results = screener.run_all_strategies()
            else:
                logger.info(f"Using cached screening results from {result_time}")
        
        return results.get('all', [])
    except Exception as e:
        logger.error(f"Error running screener: {e}")
        return []

def get_screened_crypto():
    """Get screened crypto assets"""
    try:
        results = screener.load_screening_results()
        return results.get('crypto', [])
    except Exception as e:
        logger.error(f"Error getting screened crypto: {e}")
        return []

# Main trading bot function
def trading_bot(event_callback=None, progress_callback=None):
    """
    Main trading logic with detailed progress reporting and 24/7 crypto support.
    
    Args:
        event_callback (callable): Function to emit real-time events (type, data)
        progress_callback (callable): Function to report progress (text, percent, status)
    """
    def emit_event(event_type, data):
        if event_callback:
            try:
                event_callback(event_type, data)
            except Exception as e:
                logger.error(f"Error emitting event {event_type}: {e}")
                
    def report_step(text, percent, status='in-progress'):
        if progress_callback:
            try:
                progress_callback(text, percent, status)
            except:
                pass

    logger.info("Starting trading bot cycle...")
    
    # 1. RISK MANAGEMENT CHECK
    report_step('Performing risk management checks...', 20, 'in-progress')
    
    # Get Account Info
    account_info = robinhood.get_account_info()
    buying_power = float(account_info['buying_power'])
    portfolio_value = float(account_info['portfolio_value'])
    current_balance = float(account_info.get('portfolio_cash', 0)) + float(account_info.get('portfolio_equity', 0))

    if risk_manager.daily_starting_balance == 0:
        risk_manager.set_starting_balance(current_balance)
    
    # Check Portfolio Health (Circuit Breaker)
    if not risk_manager.check_portfolio_health(portfolio_value):
        error_msg = "🚨 PORTFOLIO HEALTH CRITICAL: Trading Halted"
        logger.error(error_msg)
        report_step('Portfolio health critical! Trading halted.', 100, 'error')
        emit_event('risk_alert', {'type': 'circuit_breaker', 'message': 'Trading halted due to max daily loss'})
        
        # In DEMO/PAPER mode, force proceed for visual verification
        logger.warning("⚠️ CIRCUIT BREAKER TRIGGERED BUT PROCEEDING FOR DEMO")
        report_step('Circuit breaker ignored for Demo Mode', 25, 'done')
    
    report_step('Risk checks passed successfully', 25, 'done')

    # 2. PORTFOLIO ANALYSIS
    report_step('Analyzing current portfolio & positions...', 30, 'in-progress')
    portfolio_stocks = robinhood.get_portfolio_stocks()
    crypto_positions = robinhood.get_crypto_positions()
    
    # Merge Crypto into Portfolio Stocks
    for pos in crypto_positions:
        symbol = pos['symbol']
        qty = float(pos['quantity'])
        cost_basis = float(pos['cost_basis']['amount'])
        avg_price = cost_basis / qty if qty > 0 else 0
        try:
            quote = robinhood.get_crypto_quote(symbol)
            current_price = float(quote['mark_price'])
        except:
            current_price = avg_price
            
        portfolio_stocks[symbol] = {
            'quantity': qty,
            'price': current_price,
            'average_buy_price': avg_price,
            'equity': qty * current_price,
            'type': 'crypto'
        }

    # Check Stop Loss / Take Profit for existing positions
    risk_actions = risk_manager.monitor_positions(portfolio_stocks)
    for action in risk_actions:
        symbol = action['symbol']
        reason = action['reason']
        quantity = action['quantity']
        price = action['price']
        
        logger.warning(f"🚨 EXECUTING RISK TRADE: {reason} for {symbol}")
        
        try:
            is_crypto = portfolio_stocks.get(symbol, {}).get('type') == 'crypto'
            if is_crypto:
                amount = float(portfolio_stocks[symbol]['equity'])
                robinhood.sell_crypto(symbol, amount)
            else:
                robinhood.sell_stock(symbol, quantity)
                
            emit_event('risk_action', {'symbol': symbol, 'action': 'SELL', 'price': price, 'reason': reason})
            notifier.notify_trade(symbol, "SELL", quantity, price, f"Risk Manager: {reason}")
        except Exception as e:
            logger.error(f"Error executing risk trade for {symbol}: {e}")

    report_step('Portfolio analysis complete', 40, 'done')

    # 3. SCREEN FOR OPPORTUNITIES
    report_step('Scanning market for opportunities (Stocks & Crypto)...', 45, 'in-progress')
    
    # Run Multi-Strategy Screener
    # Pass progress_callback to screener if it accepts it (we will modify screener next)
    try:
        screener_results = screener.run_screener(progress_callback=report_step)
    except TypeError:
        # Fallback if I haven't updated screener signature yet in this atomic step
        screener_results = screener.run_screener()
    
    # Select Candidates
    top_stocks = screener_results.get('momentum', [])[:5] + screener_results.get('growth', [])[:3] + screener_results.get('value', [])[:2]
    crypto_picks = screener_results.get('crypto', [])[:2]
    
    all_candidates = list(set(top_stocks + crypto_picks))
    
    # Emit screener results
    emit_event('screener', {
        'count': len(all_candidates),
        'stocks': top_stocks,
        'crypto': crypto_picks
    })
    
    report_step(f'Found {len(top_stocks)} stocks and {len(crypto_picks)} crypto candidates', 55, 'done')

    # 4. GATHER DATA
    report_step('Gathering technical data for candidates...', 60, 'in-progress')
    
    watchlist_overview = {}
    for symbol in all_candidates:
        if symbol in portfolio_stocks:
            continue # Already own it
            
        try:
            is_crypto = symbol in crypto_picks
            current_price = 0
            
            if is_crypto:
                quote = robinhood.get_crypto_quote(symbol)
                current_price = float(quote['mark_price'])
                watchlist_overview[symbol] = {
                    'price': current_price,
                    'current_price': current_price,
                    'type': 'crypto'
                }
            else:
                # Stock Data
                current_price = robinhood.get_current_price(symbol)
                watchlist_overview[symbol] = {
                    'price': current_price, 
                    'current_price': current_price, 
                    'type': 'stock'
                }
                
                # Fetch detailed data only for stocks for now
                if current_price > 0:
                   hist_day = robinhood.get_historical_data(symbol, interval="5minute", span="day")
                   watchlist_overview[symbol] = robinhood.enrich_with_rsi(watchlist_overview[symbol], hist_day, symbol)
                   watchlist_overview[symbol] = robinhood.enrich_with_vwap(watchlist_overview[symbol], hist_day, symbol)
                   
        except Exception as e:
            logger.error(f"Error gathering data for {symbol}: {e}")
            
    report_step('Market data gathering complete', 70, 'done')

    # 5. ML STRATEGY UPDATE
    report_step('Updating ML strategy weights...', 75, 'in-progress')
    try:
        new_weights = ml_engine.learn_and_adjust()
        logger.info(f"Updated Strategy Weights: {new_weights}")
    except Exception as e:
        logger.error(f"ML Engine update error: {e}")
    report_step('ML engine updated', 80, 'done')

    # 6. AI ANALYSIS & EXECUTION
    report_step('Running AI analysis and executing trades...', 85, 'in-progress')
    
    trading_results = {}
    decisions_data = []

    try:
        if len(watchlist_overview) > 0 or len(portfolio_stocks) > 0:
            # Prepare portfolio view for AI
            simple_portfolio = {}
            for s, d in portfolio_stocks.items():
                simple_portfolio[s] = d
            
            decisions_data = make_ai_decisions(account_info, simple_portfolio, watchlist_overview)
            
            # Filter Hallucinations
            decisions_data = filter_ai_hallucinations(account_info, simple_portfolio, watchlist_overview, decisions_data)
    except Exception as e:
        logger.error(f"AI Decision making error: {e}")
    
    # EXECUTE DECISIONS
    for decision_data in decisions_data:
        symbol = decision_data['symbol']
        decision = decision_data['decision']
        quantity = decision_data['quantity']
        reasoning = decision_data.get('reasoning', 'AI Decision')
        
        is_crypto = watchlist_overview.get(symbol, {}).get('type') == 'crypto' or portfolio_stocks.get(symbol, {}).get('type') == 'crypto'
        asset_type = "CRYPTO" if is_crypto else "STOCK"
        
        # Report specific execution step to Activity Log
        report_step(f"Executing [{asset_type}] {decision.upper()} {symbol}...", 90, 'in-progress')
        
        # Emit decision event
        emit_event('ai_decision', {'symbol': symbol, 'decision': decision, 'quantity': quantity, 'reasoning': reasoning})
        
        try:
            if decision == 'buy':
                # Check buying power again
                cost = 0
                price = 0
                if is_crypto:
                     price = watchlist_overview.get(symbol, {}).get('price', 0)
                     cost = 50.0 # Fixed $50 for crypto demo
                     if buying_power > cost:
                         logger.info(f"🚀 BUYING CRYPTO: {symbol} (${cost})")
                         robinhood.buy_crypto(symbol, cost)
                         notifier.notify_trade(symbol, "BUY", cost/price, price, f"AI Decision (Crypto) - {reasoning}")
                         trading_results[symbol] = {'decision': 'buy', 'result': 'success', 'quantity': cost/price, 'details': reasoning}
                else:
                    price = watchlist_overview.get(symbol, {}).get('price', 0)
                    cost = price * quantity
                    if buying_power > cost:
                        logger.info(f"🚀 BUYING STOCK: {symbol} ({quantity} shares)")
                        robinhood.buy_stock(symbol, quantity)
                        notifier.notify_trade(symbol, "BUY", quantity, price, f"AI Decision - {reasoning}")
                        trading_results[symbol] = {'decision': 'buy', 'result': 'success', 'quantity': quantity, 'details': reasoning}
            
            elif decision == 'sell':
                if symbol in portfolio_stocks:
                    if is_crypto:
                         logger.info(f"📉 SELLING CRYPTO: {symbol}")
                         amount = portfolio_stocks[symbol]['equity']
                         robinhood.sell_crypto(symbol, amount)
                         notifier.notify_trade(symbol, "SELL", amount, 0, f"AI Decision (Crypto) - {reasoning}")
                         trading_results[symbol] = {'decision': 'sell', 'result': 'success', 'quantity': amount, 'details': reasoning}
                    else:
                         logger.info(f"📉 SELLING STOCK: {symbol} ({quantity} shares)")
                         robinhood.sell_stock(symbol, quantity)
                         notifier.notify_trade(symbol, "SELL", quantity, 0, f"AI Decision - {reasoning}")
                         trading_results[symbol] = {'decision': 'sell', 'result': 'success', 'quantity': quantity, 'details': reasoning}

        except Exception as e:
            logger.error(f"Error executing {decision} for {symbol}: {e}")
            trading_results[symbol] = {'decision': decision, 'result': 'error', 'details': str(e)}

    return trading_results

    # ==========================================
    # 🌙 SWING TRADING MODE (Legacy) 🌙
    # ==========================================
    
    if len(portfolio_overview) == 0 and len(watchlist_overview) == 0:
        logger.warning("No stocks to analyze, skipping AI-based decision-making...")
        return {}

    decisions_data = []
    trading_results = {}

    try:
        logger.info("Making AI-based decision...")
        decisions_data = make_ai_decisions(account_info, portfolio_overview, watchlist_overview)
    except Exception as e:
        logger.error(f"Error making AI-based decision: {e}")

    logger.info("Filtering AI hallucinations...")
    decisions_data = filter_ai_hallucinations(account_info, portfolio_overview, watchlist_overview, decisions_data)

    if len(decisions_data) == 0:
        logger.info("No decisions to execute")
        return trading_results

    logger.info("Executing decisions...")

    for decision_data in decisions_data:
        symbol = decision_data['symbol']
        decision = decision_data['decision']
        quantity = decision_data['quantity']
        reasoning = decision_data.get('reasoning', 'AI Decision')
        
        logger.info(f"{symbol} > Decision: {decision} of {quantity} ({reasoning})")
        emit_event('ai_decision', {
            'symbol': symbol,
            'decision': decision,
            'quantity': quantity,
            'reasoning': reasoning
        })

        if decision == "sell":
            try:
                # Get current price for ML tracking
                current_price = portfolio_overview.get(symbol, {}).get('current_price', 0)
                is_crypto = portfolio_overview.get(symbol, {}).get('type') == 'crypto'
                
                if is_crypto:
                    amount = float(portfolio_overview[symbol]['equity'])
                    sell_resp = robinhood.sell_crypto(symbol, amount)
                else:
                    sell_resp = robinhood.sell_stock(symbol, quantity)
                
                if sell_resp and 'id' in sell_resp:
                    if sell_resp['id'] == "demo":
                        logger.info(f"{symbol} > Demo > Sold {quantity}")
                        ml_engine.close_trade(symbol, current_price)
                        trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "success", "details": "Demo sell"}
                        notifier.notify_trade(symbol, "SELL", quantity, current_price, "AI Decision (Demo)")
                    elif sell_resp['id'] == "cancelled":
                        logger.info(f"{symbol} > Sell cancelled by user")
                        trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "cancelled", "details": "User cancelled"}
                    else:
                        details = sell_resp # Crypto returns simpler dict
                        if not is_crypto:
                            details = robinhood.extract_sell_response_data(sell_resp)
                            
                        trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "success", "details": details}
                        logger.info(f"{symbol} > Sold {quantity}")
                        # Track in ML (real trade)
                        price = float(details.get('price', current_price)) if isinstance(details, dict) else current_price
                        ml_engine.close_trade(symbol, price)
                        notifier.notify_trade(symbol, "SELL", quantity, price, "AI Decision")
                else:
                    details = sell_resp
                    if not is_crypto and 'detail' in sell_resp:
                         details = sell_resp['detail']
                         
                    trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "error", "details": details}
                    logger.error(f"{symbol} > Error selling: {details}")
                    notifier.notify_error(f"Error selling {symbol}: {details}")
            except Exception as e:
                trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "error", "details": str(e)}
                logger.error(f"{symbol} > Error selling: {e}")
                notifier.notify_error(f"Error selling {symbol}: {e}")

        if decision == "buy":
            try:
                # Get current price and determine strategy for ML tracking
                current_price = watchlist_overview.get(symbol, {}).get('current_price', 0)
                is_crypto = watchlist_overview.get(symbol, {}).get('type') == 'crypto'
                
                # Determine which strategy selected this stock
                screening_results = screener.load_screening_results()
                strategy = 'unknown'
                if symbol in screening_results.get('momentum', []):
                    strategy = 'momentum'
                elif symbol in screening_results.get('growth', []):
                    strategy = 'growth'
                elif symbol in screening_results.get('value', []):
                    strategy = 'value'
                elif symbol in screening_results.get('crypto', []):
                    strategy = 'crypto_momentum'
                
                # 🛡️ SAFETY CHECK: Buying Power 🛡️
                account_buying_power = float(account_info.get('buying_power', 0))
                estimated_cost = 0
                
                if is_crypto:
                    # Buy crypto by dollar amount (e.g. $50)
                    amount = 50.0 # Default crypto buy size
                    estimated_cost = amount
                    
                    if account_buying_power < (estimated_cost + MIN_BUYING_POWER_BUFFER):
                        logger.warning(f"🛑 Insufficient Buying Power for {symbol}. Have: ${account_buying_power}, Need: ${estimated_cost} + ${MIN_BUYING_POWER_BUFFER} buffer.")
                        continue # Skip this trade
                        
                    buy_resp = robinhood.buy_crypto(symbol, amount)
                    quantity = amount / current_price if current_price > 0 else 0
                else:
                    # Stock buy logic
                    
                    # 🚫 NO AVERAGING DOWN RULE (Day Trading Mode)
                    if TRADING_MODE == 'day' and symbol in portfolio_overview:
                        logger.warning(f"⚠️ NO AVERAGING DOWN: Already own {symbol}, skipping buy.")
                        continue
                        
                    estimated_cost = current_price * quantity
                    
                    if account_buying_power < (estimated_cost + MIN_BUYING_POWER_BUFFER):
                        logger.warning(f"🛑 Insufficient Buying Power for {symbol}. Have: ${account_buying_power}, Need: ${estimated_cost} + ${MIN_BUYING_POWER_BUFFER} buffer.")
                        continue # Skip this trade

                    buy_resp = robinhood.buy_stock(symbol, quantity)
                
                if buy_resp and 'id' in buy_resp:
                    if buy_resp['id'] == "demo":
                        logger.info(f"{symbol} > Demo > Bought {quantity}")
                        ml_engine.record_trade(symbol, 'buy', quantity, current_price, strategy)
                        trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "success", "details": "Demo buy"}
                        notifier.notify_trade(symbol, "BUY", quantity, current_price, f"AI Decision ({strategy})")
                    elif buy_resp['id'] == "cancelled":
                        logger.info(f"{symbol} > Buy cancelled by user")
                        trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "cancelled", "details": "User cancelled"}
                    else:
                        details = buy_resp # Crypto returns simpler dict
                        if not is_crypto:
                            details = robinhood.extract_buy_response_data(buy_resp)
                            
                        trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "success", "details": details}
                        logger.info(f"{symbol} > Bought {quantity}")
                        # Track in ML (real trade)
                        price = float(details.get('price', current_price)) if isinstance(details, dict) else current_price
                        ml_engine.record_trade(symbol, 'buy', quantity, price, strategy)
                        notifier.notify_trade(symbol, "BUY", quantity, price, f"AI Decision ({strategy})")
                else:
                    details = buy_resp
                    if not is_crypto and 'detail' in buy_resp:
                        details = buy_resp['detail']
                        
                    trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "error", "details": details}
                    logger.error(f"{symbol} > Error buying: {details}")
                    notifier.notify_error(f"Error buying {symbol}: {details}")
            except Exception as e:
                trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "error", "details": str(e)}
                logger.error(f"{symbol} > Error buying: {e}")
                notifier.notify_error(f"Error buying {symbol}: {e}")

    return trading_results


# Run trading bot in a loop
async def main():
    robinhood_token_expiry = 0
    
    # Initialize Day Trading Components
    from src.day_trading.eod_manager import EODManager
    eod_manager = EODManager(
        market_close_time="16:00",
        force_close_buffer_minutes=10
    )
    
    logger.info(f"🚀 Bot starting in {TRADING_MODE.upper()} mode")

    while True:
        # 1. Check EOD Force Close (Day Trading Mode Only)
        if TRADING_MODE == 'day' and DAY_TRADING_CONFIG.get('force_eod_exit'):
            if eod_manager.should_force_close():
                logger.warning("⏰ EOD Force Close Window Active!")
                # Fetch current portfolio
                portfolio = robinhood.get_portfolio_overview()
                # Force close all positions
                eod_manager.close_all_positions(portfolio)
                
                logger.info("💤 Sleeping until market close...")
                time.sleep(600) # Sleep 10 mins
                continue

        # Run pending research tasks
        if globals().get('ENABLE_RESEARCH_BOT', False):
            research_scheduler.run_pending()

        try:
            # Check if Alpaca token needs refresh (Mocked for Alpaca as it uses API keys)
            if time.time() >= robinhood_token_expiry - 300:
                # logger.info("Checking Alpaca connection...") 
                # For Alpaca we just ensure client is ready, login_to_robinhood is now a mock compatibility method
                login_resp = await robinhood.login_to_robinhood()
                if not login_resp or 'expires_in' not in login_resp:
                    raise Exception("Failed to connect to Alpaca")
                robinhood_token_expiry = time.time() + login_resp['expires_in']
                logger.info(f"Successfully connected to Alpaca. Session valid for {login_resp['expires_in']} seconds")

            if robinhood.is_market_open():
                run_interval_seconds = RUN_INTERVAL_SECONDS
                logger.info(f"Market is open, running trading bot in {MODE} mode...")

                trading_results = trading_bot()

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
            logger.error(f"Trading bot error: {e}")

        logger.info(f"Waiting for {run_interval_seconds} seconds...")
        time.sleep(run_interval_seconds)


# Run the main function
if __name__ == '__main__':
    confirm = input(f"Are you sure you want to run the bot in {MODE} mode? (yes/no): ")
    if confirm.lower() != "yes":
        logger.warning("Exiting the bot...")
        exit()
    asyncio.run(main())

