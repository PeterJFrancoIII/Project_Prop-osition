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
        
    def send_drawdown_warning(self, account, pct_to_max: float):
        """
        Sends an urgent alert when an account is nearing its max drawdown limit.
        """
        if not self.is_configured:
            return
            
        embed = {
            "title": f"⚠️ DRAWDOWN WARNING: {account.name}",
            "color": 0xFF8C00, # Dark Orange
            "description": f"Account is {pct_to_max:.1f}% of the way to MAX LOSS.",
            "fields": [
                {"name": "Current Equity", "value": f"${account.current_equity:,.2f}", "inline": True},
                {"name": "Total Drawdown", "value": f"{account.total_drawdown_pct:.2f}%", "inline": True},
                {"name": "Max Allowed", "value": f"{account.max_total_drawdown_pct:.2f}%", "inline": True},
            ],
            "footer": {"text": "Auto-Trader Risk Manager"}
        }
        self._dispatch(embed)

    def send_eod_report(self, accounts):
        """
        Sends an End-of-Day summary of all active accounts.
        """
        if not self.is_configured:
            return
            
        fields = []
        for acc in accounts:
            status = "🟢 Pass" if acc.is_passing else "🔴 Fail"
            fields.append({
                "name": f"{acc.name} ({status})",
                "value": f"Equity: ${acc.current_equity:,.2f} | PnL: ${acc.total_pnl:,.2f} | Target: {acc.progress_pct:.1f}%",
                "inline": False
            })
            
        embed = {
            "title": "📊 End of Day Portfolio Report",
            "color": 0x9B59B6, # Purple
            "description": f"Daily closing summary for {len(accounts)} active accounts.",
            "fields": fields,
            "footer": {"text": "Auto-Trader Portfolio Tracker"}
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
