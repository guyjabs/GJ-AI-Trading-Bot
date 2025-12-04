"""
Notification System for GJ AI Trading Bot.
Sends alerts to Discord and Telegram.
"""

import requests
import json
from datetime import datetime
from .utils import logger

# Configure your webhooks here
DISCORD_WEBHOOK_URL = ""  # Paste your Discord Webhook URL here
TELEGRAM_BOT_TOKEN = ""   # Paste your Telegram Bot Token here
TELEGRAM_CHAT_ID = ""     # Paste your Telegram Chat ID here

class NotificationSystem:
    def __init__(self):
        self.discord_enabled = bool(DISCORD_WEBHOOK_URL)
        self.telegram_enabled = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        
        if self.discord_enabled:
            logger.info("✅ Discord notifications enabled")
        if self.telegram_enabled:
            logger.info("✅ Telegram notifications enabled")

    def send_discord_message(self, title: str, description: str, color: int = 0x00ff00):
        """Send embed message to Discord"""
        if not self.discord_enabled:
            return

        data = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "GJ AI Trading Bot 🤖"}
            }]
        }
        
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=data)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")

    def send_telegram_message(self, message: str):
        """Send message to Telegram"""
        if not self.telegram_enabled:
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    def notify_trade(self, symbol: str, action: str, quantity: float, price: float, reason: str = ""):
        """Send trade alert"""
        emoji = "🟢" if action.lower() == "buy" else "🔴"
        title = f"{emoji} Trade Executed: {action.upper()} {symbol}"
        
        description = (
            f"**Symbol:** {symbol}\n"
            f"**Action:** {action.upper()}\n"
            f"**Quantity:** {quantity}\n"
            f"**Price:** ${price:.2f}\n"
            f"**Total:** ${quantity * price:.2f}\n"
        )
        
        if reason:
            description += f"**Reason:** {reason}"
            
        color = 0x00ff00 if action.lower() == "buy" else 0xff0000
        
        self.send_discord_message(title, description, color)
        self.send_telegram_message(f"{title}\n\n{description.replace('**', '*')}")

    def notify_error(self, error_msg: str):
        """Send error alert"""
        title = "⚠️ Error Alert"
        description = f"**Error:** {error_msg}"
        self.send_discord_message(title, description, 0xffa500) # Orange
        self.send_telegram_message(f"⚠️ *Error Alert*\n\nError: {error_msg}")

    def notify_daily_summary(self, summary: str):
        """Send daily summary"""
        title = "📊 Daily Summary"
        self.send_discord_message(title, summary, 0x0000ff) # Blue
        self.send_telegram_message(f"📊 *Daily Summary*\n\n{summary}")

# Global instance
notifier = NotificationSystem()
