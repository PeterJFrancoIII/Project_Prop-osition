"""
Signal executor — the core trade execution pipeline.

Receives validated signals from the webhook receiver, runs risk checks,
routes to the appropriate broker, and logs the result.
"""

import logging
from decimal import Decimal

from .models import Trade
from apps.risk_management.risk_checker import check_trade
from apps.broker_connector.alpaca_client import AlpacaClient

logger = logging.getLogger(__name__)


def execute_signal(signal: dict) -> Trade:
    """
    Execute a validated trade signal through the full pipeline.

    Pipeline: signal → risk check → broker order → trade record.

    Args:
        signal: Validated signal dict with keys:
            ticker, action, quantity, price, strategy, timestamp.

    Returns:
        Trade object with execution results.

    Raises:
        Exception: If broker order submission fails.
    """
    # --- Step 1: Create pending trade record ---
    trade = Trade.objects.create(
        symbol=signal["ticker"],
        side=signal["action"],
        quantity=Decimal(signal["quantity"]),
        requested_price=Decimal(signal.get("price", "0")) or None,
        strategy=signal["strategy"],
        status="pending",
    )
    logger.info("Trade %s created: %s %s %s", trade.trade_id, trade.side, trade.quantity, trade.symbol)

    # --- Step 2: Risk check ---
    approved, reason = check_trade(signal, account=None)
    trade.risk_approved = approved
    trade.risk_reason = reason

    if not approved:
        trade.status = "rejected"
        trade.error_message = f"Risk check failed: {reason}"
        trade.save()
        logger.warning("Trade %s rejected by risk check: %s", trade.trade_id, reason)
        return trade

    # --- Step 3: Submit to broker ---
    try:
        client = AlpacaClient()
        order_result = client.submit_order(
            symbol=signal["ticker"],
            qty=float(signal["quantity"]),
            side=signal["action"],
            order_type="market",
            time_in_force="day",
        )

        trade.broker_order_id = order_result.get("order_id", "")
        trade.status = "submitted"
        if order_result.get("filled_avg_price"):
            trade.fill_price = Decimal(str(order_result["filled_avg_price"]))
            trade.status = "filled"

        trade.save()
        logger.info("Trade %s submitted → broker order %s", trade.trade_id, trade.broker_order_id)

    except Exception as e:
        trade.status = "error"
        trade.error_message = str(e)
        trade.save()
        logger.error("Trade %s failed: %s", trade.trade_id, e, exc_info=True)
        raise

    return trade
