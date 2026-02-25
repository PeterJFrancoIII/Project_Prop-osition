"""
Signal executor — the core trade execution pipeline.

Receives validated signals from the webhook receiver, runs risk checks,
routes to the appropriate broker, and logs the result.
Layer 1: Includes cost basis tracking and realized P&L calculation.
"""

import logging
from decimal import Decimal

from django.db.models import Sum, F

from .models import Trade
from apps.risk_management.risk_checker import check_trade
from apps.broker_connector.alpaca_client import AlpacaClient

logger = logging.getLogger(__name__)


def execute_signal(signal: dict) -> Trade:
    """
    Execute a validated trade signal through the full pipeline.

    Pipeline: signal → risk check → broker order → cost basis → trade record.

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

        # --- Step 4: Cost basis and P&L tracking ---
        if trade.status == "filled" and trade.fill_price:
            _update_cost_basis(trade)

        trade.save()
        logger.info("Trade %s submitted → broker order %s", trade.trade_id, trade.broker_order_id)

    except Exception as e:
        trade.status = "error"
        trade.error_message = str(e)
        trade.save()
        logger.error("Trade %s failed: %s", trade.trade_id, e, exc_info=True)
        raise

    return trade


def _update_cost_basis(trade: Trade):
    """
    Track cost basis for buys, calculate realized P&L for sells.

    Buy: cost_basis = fill_price
    Sell: realized_pnl = (fill_price - avg_cost_basis) × quantity
    """
    if trade.side == "buy":
        # On buy, record cost basis as the fill price
        trade.cost_basis = trade.fill_price
        logger.info(
            "Trade %s: cost basis set to %s for %s",
            trade.trade_id, trade.cost_basis, trade.symbol,
        )

    elif trade.side == "sell":
        # Look up average cost basis from previous buys of same symbol
        avg_cost = _get_average_cost_basis(trade.symbol)

        if avg_cost and avg_cost > 0:
            trade.cost_basis = avg_cost
            trade.realized_pnl = (trade.fill_price - avg_cost) * trade.quantity
            logger.info(
                "Trade %s: sell %s @ %s, cost basis %s, P&L: %s",
                trade.trade_id, trade.symbol, trade.fill_price,
                avg_cost, trade.realized_pnl,
            )
        else:
            # No cost basis found — can't calculate P&L
            trade.realized_pnl = Decimal("0.00")
            logger.warning(
                "Trade %s: no cost basis found for %s — P&L set to 0",
                trade.trade_id, trade.symbol,
            )


def _get_average_cost_basis(symbol: str) -> Decimal | None:
    """
    Calculate the average cost basis for a symbol from all filled buys.

    Returns the weighted average price (total cost / total shares).
    """
    buys = Trade.objects.filter(
        symbol=symbol, side="buy", status="filled",
        cost_basis__isnull=False, cost_basis__gt=0,
    )

    if not buys.exists():
        return None

    # Weighted average: sum(cost_basis × quantity) / sum(quantity)
    result = buys.aggregate(
        total_cost=Sum(F("cost_basis") * F("quantity")),
        total_qty=Sum("quantity"),
    )

    if result["total_qty"] and result["total_qty"] > 0:
        return result["total_cost"] / result["total_qty"]

    return None
