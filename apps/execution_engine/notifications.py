import os
import requests
import logging

logger = logging.getLogger(__name__)

class DiscordNotifier:
    """
    Handles sending rich embed notifications to a Discord channel via Webhook.
    Crucial for real-time monitoring of trades, errors, and system events.
    """
    
    def __init__(self):
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        # Ensure we don't crash if webhook isn't configured in dev mock
        self.is_configured = bool(self.webhook_url)

    def send_trade_alert(self, trade):
        """
        Broadcasts an executed trade to the team Discord.
        """
        if not self.is_configured:
            return
            
        color = 0x00FF00 if trade.side.lower() == "buy" else 0xFF0000
        
        fields = [
            {"name": "Action", "value": f"{trade.side.upper()}", "inline": True},
            {"name": "Quantity", "value": f"{trade.quantity}", "inline": True},
            {"name": "Price", "value": f"${trade.price}", "inline": True},
            {"name": "Strategy", "value": f"{trade.strategy}", "inline": False},
        ]
        
        # If it was a sell with P&L, append it
        if trade.side.lower() == "sell" and getattr(trade, "realized_pnl", None):
            pnl = float(trade.realized_pnl)
            pnl_str = f"+${pnl:.2f} 🟢" if pnl > 0 else f"-${abs(pnl):.2f} 🔴"
            fields.append({"name": "Realized P&L", "value": pnl_str, "inline": False})
            
        embed = {
            "title": f"🚨 TRADE EXECUTED: {trade.symbol}",
            "color": color,
            "fields": fields,
            "footer": {"text": "Auto-Trader AI Brain"}
        }
            
        self._dispatch(embed)
        
    def send_system_alert(self, title: str, message: str, level: str = "INFO"):
        """
        Broadcasts system events (API errors, celery task crashes, etc).
        """
        if not self.is_configured:
            return
            
        colors = {
            "INFO": 0x3498DB,
            "WARNING": 0xF1C40F,
            "ERROR": 0xE74C3C,
            "CRITICAL": 0x992D22,
        }
        
        embed = {
            "title": f"[{level}] {title}",
            "description": message,
            "color": colors.get(level.upper(), 0xFFFFFF),
            "footer": {"text": "Auto-Trader System Monitor"}
        }
        
        self._dispatch(embed)
        
    def _dispatch(self, embed: dict):
        if not self.webhook_url:
            return
            
        payload = {"embeds": [embed]}
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=5)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to push alert to Discord: {e}")
