import time
from datetime import datetime
import json
import asyncio

from config import *
from src.api import robinhood
from src.api import openai
from src.utils import logger
from src.screener import screener
from src.ml_engine import ml_engine
from src.risk_manager import risk_manager
from src.notifications import notifier
from src.research import NewsAggregator, KnowledgeBase, TrendAnalyzer, StrategyResearcher, ResearchScheduler

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
        '  {"symbol": <symbol>, "decision": <decision>, "quantity": <quantity>},\n'
        "  ...\n"
        "]\n"
        "```\n"
        "- <symbol>: Stock symbol.\n"
        "- <decision>: One of `buy`, `sell`, or `hold`.\n"
        "- <quantity>: Recommended transaction quantity.\n\n"
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
def trading_bot():
    logger.info("Getting account info...")
    account_info = robinhood.get_account_info()
    
    # 🔒 SAFETY LOG 🔒
    if not ENABLE_BANK_TRANSFERS:
        logger.info("🔒 Bank Transfers are DISABLED. Using only available buying power.")
    else:
        logger.warning("⚠️ Bank Transfers are ENABLED in config. Please verify this is intended.")
    
    # Initialize Risk Manager with current balance
    current_balance = float(account_info.get('portfolio_cash', 0)) + float(account_info.get('portfolio_equity', 0))
    if risk_manager.daily_starting_balance == 0:
        risk_manager.set_starting_balance(current_balance)
        
    # Check Circuit Breaker
    if not risk_manager.check_portfolio_health(current_balance):
        logger.critical("⚠️ TRADING HALTED DUE TO CIRCUIT BREAKER ⚠️")
        return {}

    logger.info("Getting portfolio stocks...")
    portfolio_stocks = robinhood.get_portfolio_stocks()
    
    # Get Crypto Positions
    logger.info("Getting crypto positions...")
    crypto_positions = robinhood.get_crypto_positions()
    
    # Merge Crypto into Portfolio Stocks for unified view/risk management
    for pos in crypto_positions:
        symbol = pos['symbol'] # e.g. BTC
        qty = float(pos['quantity'])
        cost_basis = float(pos['cost_basis']['amount'])
        avg_price = cost_basis / qty if qty > 0 else 0
        
        # Get current price
        try:
            quote = robinhood.get_crypto_quote(symbol)
            current_price = float(quote['mark_price'])
        except:
            current_price = avg_price # Fallback
            
        portfolio_stocks[symbol] = {
            'quantity': qty,
            'price': current_price,
            'average_buy_price': avg_price,
            'equity': qty * current_price,
            'type': 'crypto' # Mark as crypto
        }

    logger.debug(f"Portfolio total items: {len(portfolio_stocks)}")

    portfolio_stocks_value = 0
    for stock in portfolio_stocks.values():
        portfolio_stocks_value += float(stock['price']) * float(stock['quantity'])
    portfolio = []
    if portfolio_stocks_value > 0:
        portfolio = [f"{symbol} ({round(float(stock['price']) * float(stock['quantity']) / portfolio_stocks_value * 100, 2)}%)" for symbol, stock in portfolio_stocks.items()]
    logger.info(f"Portfolio items to proceed: {'None' if len(portfolio) == 0 else ', '.join(portfolio)}")

    # 🛡️ RISK MANAGEMENT CHECK 🛡️
    # Check for Stop-Loss / Take-Profit triggers BEFORE AI analysis
    logger.info("Running Risk Management checks...")
    risk_actions = risk_manager.monitor_positions(portfolio_stocks)
    
    # Execute Risk Management Trades immediately
    for action in risk_actions:
        symbol = action['symbol']
        reason = action['reason']
        quantity = action['quantity']
        
        logger.warning(f"🚨 EXECUTING RISK MANAGEMENT TRADE: {reason} for {symbol}")
        
        try:
            is_crypto = portfolio_stocks.get(symbol, {}).get('type') == 'crypto'
            
            # Execute sell immediately
            if is_crypto:
                # Sell crypto by dollar amount (sell all)
                amount = float(portfolio_stocks[symbol]['equity'])
                sell_resp = robinhood.sell_crypto(symbol, amount)
            else:
                sell_resp = robinhood.sell_stock(symbol, quantity)
            
            if sell_resp and 'id' in sell_resp:
                if sell_resp['id'] == "demo":
                    logger.info(f"{symbol} > Demo > Risk Sell ({reason}) executed")
                    ml_engine.close_trade(symbol, action['price'])
                else:
                    logger.info(f"{symbol} > Risk Sell ({reason}) executed")
                    ml_engine.close_trade(symbol, action['price'])
                    notifier.notify_trade(symbol, "SELL", quantity, action['price'], f"Risk Manager: {reason}")
                    
                # Add to results so we don't try to sell again in AI step
                trading_results[symbol] = {
                    "symbol": symbol, 
                    "quantity": quantity, 
                    "decision": "sell", 
                    "result": "success", 
                    "details": f"Risk Manager: {reason}"
                }
            else:
                logger.error(f"{symbol} > Risk Sell failed: {sell_resp}")
                notifier.notify_error(f"Risk Sell failed for {symbol}: {sell_resp}")
                
        except Exception as e:
            logger.error(f"Error executing risk trade for {symbol}: {e}")
            notifier.notify_error(f"Error executing risk trade for {symbol}: {e}")

    logger.info("Prepare portfolio stocks for AI analysis...")
    portfolio_overview = {}
    for symbol, stock_data in portfolio_stocks.items():
        # Simplified portfolio_overview for AI analysis, including type
        portfolio_overview[symbol] = {
            "price": float(stock_data['price']), 
            "quantity": float(stock_data['quantity']), 
            "average_buy_price": float(stock_data['average_buy_price']),
            "equity": float(stock_data.get('equity', 0)),
            "type": stock_data.get('type', 'stock')
        }
        # Enrich with historical data and ratings if it's a stock
        if portfolio_overview[symbol]['type'] == 'stock':
            historical_data_day = robinhood.get_historical_data(symbol, interval="5minute", span="day")
            historical_data_year = robinhood.get_historical_data(symbol, interval="day", span="year")
            ratings_data = robinhood.get_ratings(symbol)
            portfolio_overview[symbol] = robinhood.enrich_with_rsi(portfolio_overview[symbol], historical_data_day, symbol)
            portfolio_overview[symbol] = robinhood.enrich_with_vwap(portfolio_overview[symbol], historical_data_day, symbol)
            portfolio_overview[symbol] = robinhood.enrich_with_moving_averages(portfolio_overview[symbol], historical_data_year, symbol)
            portfolio_overview[symbol] = robinhood.enrich_with_analyst_ratings(portfolio_overview[symbol], ratings_data)
            portfolio_overview[symbol] = robinhood.enrich_with_pdt_restrictions(portfolio_overview[symbol], symbol)


    # Get stocks from screener instead of manual watchlists
    logger.info("Getting stocks and crypto from AI screener...")
    screened_symbols = get_screened_stocks()
    screened_crypto = get_screened_crypto()
    
    # Also check manual watchlists if configured
    watchlist_stocks = []
    for watchlist_name in WATCHLIST_NAMES:
        try:
            watchlist_stocks.extend(robinhood.get_watchlist_stocks(watchlist_name))
            watchlist_stocks = [dict(t) for t in {tuple(d.items()) for d in watchlist_stocks}]
        except Exception as e:
            logger.error(f"Error getting watchlist stocks for {watchlist_name}: {e}")
    
    # Combine screened stocks with manual watchlist
    all_symbols = set(screened_symbols)
    all_symbols.update([s['symbol'] for s in watchlist_stocks])
    
    # Convert to watchlist format for compatibility
    watchlist_items = [{'symbol': s, 'price': 0, 'type': 'stock'} for s in all_symbols if s not in portfolio_stocks.keys()]
    
    # Add Crypto to watchlist
    for coin in screened_crypto:
        if coin not in portfolio_stocks.keys():
            watchlist_items.append({'symbol': coin, 'price': 0, 'type': 'crypto'})
    
    logger.debug(f"Total assets to analyze: {len(watchlist_items)} (stocks: {len(screened_symbols)}, crypto: {len(screened_crypto)})")

    watchlist_overview = {}
    # Prepare watchlist_overview for AI analysis
    for item in watchlist_items:
        symbol = item['symbol']
        try:
            current_price = 0
            if item.get('type') == 'crypto':
                quote = robinhood.get_crypto_quote(symbol)
                current_price = float(quote['mark_price'])
            else:
                current_price = robinhood.get_current_price(symbol)
                
            watchlist_overview[symbol] = {
                "price": current_price, 
                "current_price": current_price,
                "type": item.get('type', 'stock')
            }
            
            # Enrich with historical data and ratings if it's a stock
            if watchlist_overview[symbol]['type'] == 'stock':
                historical_data_day = robinhood.get_historical_data(symbol, interval="5minute", span="day")
                historical_data_year = robinhood.get_historical_data(symbol, interval="day", span="year")
                ratings_data = robinhood.get_ratings(symbol)
                watchlist_overview[symbol] = robinhood.enrich_with_rsi(watchlist_overview[symbol], historical_data_day, symbol)
                watchlist_overview[symbol] = robinhood.enrich_with_vwap(watchlist_overview[symbol], historical_data_day, symbol)
                watchlist_overview[symbol] = robinhood.enrich_with_moving_averages(watchlist_overview[symbol], historical_data_year, symbol)
                watchlist_overview[symbol] = robinhood.enrich_with_analyst_ratings(watchlist_overview[symbol], ratings_data)
                watchlist_overview[symbol] = robinhood.enrich_with_pdt_restrictions(watchlist_overview[symbol], symbol)

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")

    # The original watchlist_stocks limiting and filtering logic is now redundant
    # as watchlist_items already contains the combined and filtered list.
    # The enrichment for watchlist_overview is now done in the loop above.
    # The following block is removed as per the new structure.
    # if len(watchlist_stocks) > 0:
    #     logger.debug(f"Limiting watchlist stocks to overview limit of {WATCHLIST_OVERVIEW_LIMIT}...")
    #     watchlist_stocks = limit_watchlist_stocks(watchlist_stocks, WATCHLIST_OVERVIEW_LIMIT)
    #     logger.debug(f"Removing portfolio stocks from watchlist...")
    #     watchlist_stocks = [stock for stock in watchlist_stocks if stock['symbol'] not in portfolio_stocks.keys()]
    #     logger.info(f"Watchlist stocks to proceed: {', '.join([stock['symbol'] for stock in watchlist_stocks])}")
    #     logger.info("Prepare watchlist overview for AI analysis...")
    #     for stock_data in watchlist_stocks:
    #         symbol = stock_data['symbol']
    #         historical_data_day = robinhood.get_historical_data(symbol, interval="5minute", span="day")
    #         historical_data_year = robinhood.get_historical_data(symbol, interval="day", span="year")
    #         ratings_data = robinhood.get_ratings(symbol)
    #         watchlist_overview[symbol] = robinhood.extract_watchlist_data(stock_data)
    #         watchlist_overview[symbol] = robinhood.enrich_with_rsi(watchlist_overview[symbol], historical_data_day, symbol)
    #         watchlist_overview[symbol] = robinhood.enrich_with_vwap(watchlist_overview[symbol], historical_data_day, symbol)
    #         watchlist_overview[symbol] = robinhood.enrich_with_moving_averages(watchlist_overview[symbol], historical_data_year, symbol)
    #         watchlist_overview[symbol] = robinhood.enrich_with_analyst_ratings(watchlist_overview[symbol], ratings_data)
    #         watchlist_overview[symbol] = robinhood.enrich_with_pdt_restrictions(watchlist_overview[symbol], symbol)


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
        logger.info(f"{symbol} > Decision: {decision} of {quantity}")

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

    while True:
        # Run pending research tasks
        if globals().get('ENABLE_RESEARCH_BOT', False):
            research_scheduler.run_pending()

        try:
            # Check if Robinhood token needs refresh (refresh 5 minutes before expiry)
            if time.time() >= robinhood_token_expiry - 300:
                logger.info("Login to Robinhood...")
                login_resp = await robinhood.login_to_robinhood()
                if not login_resp or 'expires_in' not in login_resp:
                    raise Exception("Failed to login to Robinhood")
                robinhood_token_expiry = time.time() + login_resp['expires_in']
                logger.info(f"Successfully logged in. Token expires in {login_resp['expires_in']} seconds")

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

