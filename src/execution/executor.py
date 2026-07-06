from src.utils import logger
from src.notifications import notifier
from src.data.db import db # For logging

class TradeExecutor:
    """
    The Action Layer.
    Translates AI decisions into Alpaca Orders.
    Handles 'Ruthless' Position Sizing (Conviction based).
    """
    def __init__(self, client):
        self.client = client
        self.min_trade_amount = 100.0 # USD

    def execute_decision(self, decision_data, account_info, market_data):
        symbol = decision_data.get('symbol')
        action = decision_data.get('decision')
        reasoning = decision_data.get('reasoning', '')
        conviction = float(decision_data.get('conviction', 5.0))
        features = decision_data.get('features', {})
        
        # Clamp conviction
        conviction = max(1.0, min(10.0, conviction))
        
        # Get Price / Type
        data = market_data.get(symbol, {})
        price = data.get('price', 0)
        is_crypto = data.get('type') == 'crypto'
        
        # Fallback price check
        if price <= 0:
            price = self.client.get_current_price(symbol)
            if price <= 0:
                logger.warning(f"⚠️ Executor: Price 0 for {symbol}. Skipping.")
                return

        buying_power = float(account_info.get('buying_power', 0))

        if action == 'buy':
            # RUTHLESS SIZING
            alloc_pct = 0.20
            # Leverage multiplier for high conviction non-crypto trades
            if not is_crypto and conviction >= 8.0:
                logger.info(f"💎 HIGH CONVICTION ({conviction}/10). Applying 2x leverage!")
                alloc_pct = 0.40
                
            max_alloc = buying_power * alloc_pct
            # Actual allocation = Scaled by conviction
            target_alloc = max_alloc * (conviction / 10.0)
            
            if target_alloc < self.min_trade_amount:
                logger.info(f"⏭️ Skipping {symbol}: Allocation ${target_alloc:.2f} too small.")
                return

            logger.info(f"🚀 EXECUTING BUY {symbol}: Conviction {conviction}/10 -> ${target_alloc:.2f}")
            
            if is_crypto:
                if buying_power >= target_alloc:
                    self.client.buy_crypto(symbol, target_alloc)
                    self._log_trade(symbol, 'BUY', target_alloc/price, price, reasoning, features)
            else:
                qty = int(target_alloc / price)
                cost = qty * price
                if qty > 0 and buying_power >= cost:
                     self.client.buy_stock(symbol, qty)
                     self._log_trade(symbol, 'BUY', qty, price, reasoning, features)
                else:
                    logger.warning(f"⚠️ Insufficient BP/Qty for {symbol}")

        elif action == 'sell':
            # Simplified Sell Logic: Sell All
            logger.info(f"📉 EXECUTING SELL {symbol}")
            
            positions = self.client.get_portfolio_stocks()
            if symbol in positions:
                if is_crypto:
                     qty = positions[symbol]['equity']
                     self.client.sell_crypto(symbol, qty)
                     self._log_trade(symbol, 'SELL', qty, price, reasoning, features)
                else:
                     qty = positions[symbol]['quantity']
                     if qty > 0:
                         self.client.sell_stock(symbol, qty)
                         self._log_trade(symbol, 'SELL', qty, price, reasoning, features)

        elif action == 'short':
            if is_crypto:
                logger.warning(f"⚠️ Cannot short crypto {symbol}")
                return
                
            alloc_pct = 0.20
            if conviction >= 8.0:
                logger.info(f"💎 HIGH CONVICTION SHORT ({conviction}/10). Applying 2x leverage!")
                alloc_pct = 0.40
                
            max_alloc = buying_power * alloc_pct
            target_alloc = max_alloc * (conviction / 10.0)
            
            if target_alloc < self.min_trade_amount:
                return
                
            qty = int(target_alloc / price)
            if qty > 0:
                logger.info(f"🐻 EXECUTING SHORT {symbol}: Conviction {conviction}/10 -> {qty} shares")
                self.client.sell_stock(symbol, qty) # Alpaca handles short selling via sell order
                self._log_trade(symbol, 'SHORT', qty, price, reasoning, features)

        elif action == 'cover':
            logger.info(f"📈 EXECUTING COVER {symbol}")
            positions = self.client.get_portfolio_stocks()
            if symbol in positions:
                # Alpaca returns negative quantity for shorts
                qty = abs(positions[symbol]['quantity'])
                if qty > 0:
                    self.client.buy_stock(symbol, qty) # Alpaca handles covering via buy order
                    self._log_trade(symbol, 'COVER', qty, price, reasoning, features)

    def execute_risk_action(self, action):
        """Execute forced risk management trades (Stop Loss)."""
        symbol = action['symbol']
        qty = action.get('quantity')
        
        logger.warning(f"🛡️ EXECUTE RISK SELL: {symbol}")
        # Need to detect type again or pass it. 
        # For safety, try stock sell first, catch error? Or use client 'close_position' if available.
        try:
             self.client.sell_stock(symbol, qty)
             notifier.notify_trade(symbol, "SELL (RISK)", qty, 0, action.get('reason'))
        except:
             # Try crypto
             self.client.sell_crypto(symbol, qty) # Assuming qty is amount

    def _log_trade(self, symbol, side, qty, price, reason, features=None):
        notifier.notify_trade(symbol, side, qty, price, reason)
        try:
            from src.data.db import db
            from src.trade_journal import trade_journal
            db.log_trade({
                'symbol': symbol,
                'decision': side.lower(),
                'quantity': qty,
                'price': price,
                'reasoning': reason,
                'bot_name': 'QuantBot'
            })
            
            if side.upper() == 'BUY':
                trade_journal.log_entry(
                    symbol=symbol,
                    price=price,
                    shares=qty,
                    strategy="quant_model",
                    feature_vector=features
                )
            elif side.upper() == 'SELL':
                trade_journal.log_exit(
                    symbol=symbol,
                    price=price,
                    pnl=0.0, # Exact PNL calculation happens externally or next iteration
                    pnl_pct=0.0,
                    notes=reason,
                    exit_reason="signal_exit"
                )
        except Exception as e:
            logger.error(f"Error logging trade to journal: {e}")
