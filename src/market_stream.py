import threading
import asyncio
from config import ALPACA_CONFIG
from src.utils import logger
from alpaca.trading.stream import TradingStream
from alpaca.data.live.stock import StockDataStream
from alpaca.data.live.crypto import CryptoDataStream

class MarketStream:
    def __init__(self, api_key, secret_key, paper=True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        
        self.trading_stream = TradingStream(api_key, secret_key, paper=paper)
        # We might need separate streams for Stock vs Crypto data
        self.stock_stream = StockDataStream(api_key, secret_key)
        self.crypto_stream = CryptoDataStream(api_key, secret_key)
        
        self.listeners = {
            'trade_update': [],
            'price_update': []
        }
        self._stop_event = threading.Event()
        self._thread = None

    def subscribe_trade_updates(self, callback):
        """Subscribe to order status updates (fills, cancels)"""
        self.listeners['trade_update'].append(callback)

    def subscribe_quotes(self, symbols, callback):
        """Subscribe to real-time quotes for symbols"""
        self.listeners['price_update'].append(callback)
        # Note: In a real app we'd determine if symbol is stock or crypto
        # For simplicity, assuming stocks for now or try both
        try:
            self.stock_stream.subscribe_quotes(self._handle_quote, *symbols)
        except:
            pass
            
    async def _handle_trade_update(self, data):
        """Internal handler for trade updates"""
        try:
            # data is a TradeUpdate object
            event = {
                'event': data.event, # 'fill', 'new', etc.
                'symbol': data.order.symbol,
                'qty': data.order.qty,
                'price': data.order.filled_avg_price,
                'side': data.order.side,
                'status': data.order.status
            }
            for listener in self.listeners['trade_update']:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"Error in trade listener: {e}")
        except Exception as e:
            logger.error(f"Error parsing trade update: {e}")

    async def _handle_quote(self, data):
        """Internal handler for quotes"""
        # data is a Quote object
        for listener in self.listeners['price_update']:
            listener(data)

    def start(self):
        """Start the streams in a background thread"""
        if self._thread and self._thread.is_alive():
            logger.warning("Stream already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("🔴 Market Stream Started (Background)")

    def _run_loop(self):
        """Main asyncio loop for streams"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # subscribe internal handlers
        self.trading_stream.subscribe_trade_updates(self._handle_trade_update)
        
        # Run streams
        # Note: alpca-py streams are blocking. We need to run them concurrently.
        # This is complex because each 'run' blocks.
        # We will prioritize Trading Stream (Events) for Phase 2.
        # Data stream might need a separate thread if we want both.
        
        logger.info("Listening for trade updates...")
        try:
            loop.run_until_complete(self.trading_stream.run())
        except Exception as e:
            logger.error(f"Stream Error: {e}")
        finally:
            loop.close()

    def stop(self):
        self._stop_event.set()
        # Alpaca stream doesn't have a clean 'stop' from outside easily without closing loop
        # For now, we rely on daemon thread killing
        pass

# Global Instance
market_stream = MarketStream(
    ALPACA_CONFIG['api_key'], 
    ALPACA_CONFIG['secret_key'], 
    ALPACA_CONFIG['paper']
)
