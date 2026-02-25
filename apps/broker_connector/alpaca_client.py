"""
Alpaca broker client — wrapper around the Alpaca Trade API.

Handles order submission, account info, and position queries
for both paper and live trading accounts.
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy import — alpaca-trade-api may not be installed during initial setup
try:
    import alpaca_trade_api as tradeapi
except ImportError:
    tradeapi = None
    logger.warning("alpaca-trade-api not installed — Alpaca client unavailable")


class AlpacaClient:
    """
    Wrapper around the Alpaca Trade API for stock order execution.

    Supports paper trading (default) and live trading modes.
    """

    def __init__(self, api_key: str = None, secret_key: str = None, base_url: str = None):
        """
        Initialize the Alpaca client.

        Args:
            api_key: Alpaca API key (defaults to settings).
            secret_key: Alpaca secret key (defaults to settings).
            base_url: API base URL (defaults to paper trading).
        """
        if tradeapi is None:
            raise RuntimeError("alpaca-trade-api is not installed. Run: pip install alpaca-trade-api")

        self.api_key = api_key or settings.BROKER_ALPACA_API_KEY
        self.secret_key = secret_key or settings.BROKER_ALPACA_SECRET_KEY
        self.base_url = base_url or settings.BROKER_ALPACA_BASE_URL

        self.api = tradeapi.REST(
            key_id=self.api_key,
            secret_key=self.secret_key,
            base_url=self.base_url,
            api_version="v2",
        )
        logger.info("Alpaca client initialized (base_url=%s)", self.base_url)

    def get_account(self) -> dict:
        """
        Get account information (buying power, equity, cash, status).

        Returns:
            Dict with account details.
        """
        account = self.api.get_account()
        return {
            "id": account.id,
            "status": account.status,
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "pattern_day_trader": account.pattern_day_trader,
        }

    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: float = None,
        stop_price: float = None,
    ) -> dict:
        """
        Submit an order to Alpaca.

        Args:
            symbol: Stock ticker (e.g., "AAPL").
            qty: Number of shares.
            side: "buy" or "sell".
            order_type: "market", "limit", "stop", "stop_limit".
            time_in_force: "day", "gtc", "opg", "ioc".
            limit_price: Required for limit/stop_limit orders.
            stop_price: Required for stop/stop_limit orders.

        Returns:
            Dict with order details including order ID and status.
        """
        order_params = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
        }
        if limit_price is not None:
            order_params["limit_price"] = limit_price
        if stop_price is not None:
            order_params["stop_price"] = stop_price

        logger.info("Submitting order: %s %s %s @ %s", side, qty, symbol, order_type)
        order = self.api.submit_order(**order_params)

        result = {
            "order_id": order.id,
            "client_order_id": order.client_order_id,
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side,
            "type": order.type,
            "status": order.status,
            "submitted_at": str(order.submitted_at),
            "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
        }
        logger.info("Order submitted: %s (status=%s)", result["order_id"], result["status"])
        return result

    def get_positions(self) -> list:
        """
        Get all open positions.

        Returns:
            List of dicts with position details.
        """
        positions = self.api.list_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "side": p.side,
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc),
            }
            for p in positions
        ]

    def cancel_all_orders(self) -> int:
        """
        Cancel all open orders (emergency kill switch support).

        Returns:
            Number of orders cancelled.
        """
        cancelled = self.api.cancel_all_orders()
        count = len(cancelled) if cancelled else 0
        logger.warning("Kill switch: cancelled %d open orders", count)
        return count

    def close_all_positions(self) -> int:
        """
        Close all open positions (emergency kill switch support).

        Returns:
            Number of positions closed.
        """
        positions = self.api.close_all_positions()
        count = len(positions) if positions else 0
        logger.warning("Kill switch: closed %d positions", count)
        return count
