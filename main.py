
import os
import sys
from src.utils import logger
from src.bot.engine import TradingBot
from dotenv import load_dotenv

# Load Environment
load_dotenv()

def main():
    """
    Entry point for the GJ AI Trading Bot.
    """
    try:
        logger.info("🚀 Starting GJ AI Trading Bot...")
        
        bot = TradingBot()
        
        # Run one cycle immediately
        bot.run_cycle()
        
        # Scheduled runner could go here (e.g., schedule.every(1).hour.do(bot.run_cycle))
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"Fatal Bot Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
