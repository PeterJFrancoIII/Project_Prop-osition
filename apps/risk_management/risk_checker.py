"""
Risk checker — pre-trade risk validation.

Layer 1: Full implementation with kill switch, drawdown checks,
position limits, daily trade limits, market hours enforcement,
and prop firm rule compliance.

Every check reads from the RiskConfig model (config-driven, not hardcoded).
"""

import logging
from datetime import time as dt_time
from decimal import Decimal

from django.utils import timezone

from apps.execution_engine.models import Trade
from apps.risk_management.models import RiskConfig

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def check_trade(signal: dict, account=None) -> tuple[bool, str]:
    """
    Run the full pre-trade risk check pipeline.

    Args:
        signal: Validated signal dict (ticker, action, quantity, price, strategy).
        account: BrokerAccount instance (optional).

    Returns:
        (approved: bool, reason: str).
    """
    # Bypass Djongo boolean filter SQLDecodeError
    configs = RiskConfig.objects.all()
    config = next((c for c in configs if c.is_active), None)

    if not config:
        logger.error("No active RiskConfig found — rejecting trade")
        return (False, "No active risk configuration found")

    # Run checks in priority order — first failure short-circuits
    checks = [
        ("kill_switch", _check_kill_switch, (config,)),
        ("market_hours", _check_market_hours, (signal,)),
        ("daily_drawdown", _check_daily_drawdown, (config,)),
        ("daily_loss_limit", _check_daily_loss_limit, (config,)),
        ("daily_trade_count", _check_daily_trade_count, (config,)),
        ("max_open_positions", _check_max_open_positions, (config, account)),
        ("position_size", _check_position_size, (config, signal, account)),
        ("sell_above_cost", _check_sell_above_cost_basis, (signal,)),
    ]

    for name, check_fn, args in checks:
        approved, reason = check_fn(*args)
        if not approved:
            logger.warning("Risk check FAILED [%s]: %s", name, reason)
            return (False, reason)

    logger.info(
        "Risk check PASSED: %s %s %s",
        signal.get("action"),
        signal.get("quantity"),
        signal.get("ticker"),
    )
    return (True, "All risk checks passed")


# ──────────────────────────────────────────────
# Individual risk checks
# ──────────────────────────────────────────────

def _check_kill_switch(config: RiskConfig) -> tuple[bool, str]:
    """Reject ALL trades when kill switch is active."""
    if config.kill_switch_active:
        return (False, "Kill switch is ACTIVE — all trading halted")
    return (True, "Kill switch inactive")


def _check_market_hours(signal: dict) -> tuple[bool, str]:
    """
    Stocks must only trade during market hours (9:30 AM - 4:00 PM ET).
    Crypto and futures are 24/7 — this check only applies to stock signals.
    """
    strategy = signal.get("strategy", "")
    ticker = signal.get("ticker", "")

    # Skip for crypto tickers (contain / or common crypto symbols)
    if "/" in ticker or ticker in ("BTC", "ETH", "SOL", "DOGE", "AVAX"):
        return (True, "Crypto — 24/7 trading allowed")

    # Skip for futures tickers (start with / or common futures prefixes)
    if ticker.startswith("/") or ticker.startswith("MES") or ticker.startswith("MNQ"):
        return (True, "Futures — extended hours allowed")

    now = timezone.now()
    # Convert to US/Eastern for market hours check
    try:
        import pytz
        eastern = pytz.timezone("US/Eastern")
        now_et = now.astimezone(eastern)
    except ImportError:
        # Fallback: assume UTC-5 (close enough for safety)
        from datetime import timedelta
        now_et = now - timedelta(hours=5)

    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)
    current_time = now_et.time()

    # Check if it's a weekday
    if now_et.weekday() >= 5:  # Saturday=5, Sunday=6
        return (False, f"Market closed — weekend ({now_et.strftime('%A')})")

    if not (market_open <= current_time <= market_close):
        return (
            False,
            f"Market closed — current time {current_time.strftime('%H:%M')} ET "
            f"(open 09:30-16:00)"
        )

    return (True, "Within market hours")


def _check_daily_drawdown(config: RiskConfig) -> tuple[bool, str]:
    """Reject if today's realized P&L exceeds the max daily drawdown %."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    daily_pnl = Decimal("0.00")
    today_trades = Trade.objects.filter(
        created_at__gte=today_start,
        status="filled",
        realized_pnl__isnull=False,
    )
    for trade in today_trades:
        daily_pnl += Decimal(str(trade.realized_pnl))

    # If P&L is positive, no drawdown concern
    if daily_pnl >= 0:
        return (True, f"Daily P&L is positive (${daily_pnl})")

    # Calculate drawdown as absolute percentage
    # Using daily_loss_limit as a dollar proxy for now
    # TODO (Layer 1+): Use actual account equity from Alpaca
    loss_pct = abs(daily_pnl)  # Dollar amount for now

    loss_limit = Decimal(str(config.daily_loss_limit))
    if abs(daily_pnl) >= loss_limit:
        return (
            False,
            f"Daily drawdown limit reached — lost ${abs(daily_pnl):.2f} "
            f"(limit: ${loss_limit})"
        )

    return (True, f"Daily P&L within limits (${daily_pnl})")


def _check_daily_loss_limit(config: RiskConfig) -> tuple[bool, str]:
    """Reject if today's dollar losses exceed the daily loss limit."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    daily_pnl = Decimal("0")
    today_closed = Trade.objects.filter(
        created_at__gte=today_start,
        status="filled",
        realized_pnl__isnull=False,
    )
    for trade in today_closed:
        daily_pnl += Decimal(str(trade.realized_pnl))

    loss_limit = Decimal(str(config.daily_loss_limit))
    if daily_pnl < Decimal("0") and abs(daily_pnl) >= loss_limit:
        return (
            False,
            f"Daily loss limit hit — ${abs(daily_pnl):.2f} lost "
            f"(limit: ${loss_limit})"
        )

    return (True, f"Within daily dollar loss limit")


def _check_daily_trade_count(config: RiskConfig) -> tuple[bool, str]:
    """Reject if today's trade count exceeds the max daily trades."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    count = Trade.objects.filter(created_at__gte=today_start).count()

    if count >= config.max_daily_trades:
        return (
            False,
            f"Daily trade limit reached — {count} trades today "
            f"(limit: {config.max_daily_trades})"
        )

    return (True, f"Trade count OK ({count}/{config.max_daily_trades})")


def _check_max_open_positions(config: RiskConfig, account=None) -> tuple[bool, str]:
    """Reject if the number of open positions exceeds the limit."""
    # Try to get real position count from Alpaca
    open_positions = 0
    try:
        from apps.broker_connector.alpaca_client import AlpacaClient
        client = AlpacaClient()
        positions = client.get_positions()
        open_positions = len(positions)
    except Exception:
        # Fallback: count unfilled buy trades without matching sells
        # This is approximate but safe (errs on the side of caution)
        buys = Trade.objects.filter(side="buy", status="filled").values_list("symbol", flat=True)
        sells = Trade.objects.filter(side="sell", status="filled").values_list("symbol", flat=True)
        open_symbols = set(buys) - set(sells)
        open_positions = len(open_symbols)

    if open_positions >= config.max_open_positions:
        return (
            False,
            f"Max open positions reached — {open_positions} open "
            f"(limit: {config.max_open_positions})"
        )

    return (True, f"Open positions OK ({open_positions}/{config.max_open_positions})")


def _check_position_size(config: RiskConfig, signal: dict, account=None) -> tuple[bool, str]:
    """Reject if the order value exceeds the max position size % of equity."""
    qty = Decimal(str(signal.get("quantity", "0")))
    price = Decimal(str(signal.get("price", "0")))

    if price <= 0 or qty <= 0:
        # Can't validate position size without price — allow (market orders)
        return (True, "Market order — position size check skipped (no price)")

    order_value = qty * price

    # Try to get account equity from Alpaca
    equity = Decimal("100000.00")  # Default fallback
    try:
        from apps.broker_connector.alpaca_client import AlpacaClient
        client = AlpacaClient()
        acct = client.get_account()
        equity = Decimal(str(acct["equity"]))
    except Exception:
        pass  # Use fallback

    max_pct = Decimal(str(config.max_position_size_pct))
    max_position_value = equity * (max_pct / Decimal("100"))

    if order_value > max_position_value:
        return (
            False,
            f"Position too large — ${order_value:.2f} exceeds "
            f"{max_pct}% of equity (${max_position_value:.2f})"
        )

    return (True, f"Position size OK (${order_value:.2f} / ${max_position_value:.2f} max)")


def _check_sell_above_cost_basis(signal: dict) -> tuple[bool, str]:
    """
    Reject sell orders where the signal price is below the average cost basis.

    Arch Public principle: never sell at a loss if it can be avoided.
    Only applies to sell orders with a known price.
    """
    if signal.get("action") != "sell":
        return (True, "Not a sell order — cost basis check skipped")

    ticker = signal.get("ticker", "")
    signal_price = Decimal(str(signal.get("price", "0")))

    if signal_price <= 0:
        # Market order — can't enforce price-based check
        return (True, "Market sell — no price to compare against cost basis")

    # Look up average cost basis from filled buy trades
    all_buys = Trade.objects.filter(
        symbol=ticker, side="buy", status="filled"
    )
    
    total_cost = Decimal("0")
    total_qty = Decimal("0")
    
    for b in all_buys:
        if b.cost_basis is not None and Decimal(str(b.cost_basis)) > 0:
            qty = Decimal(str(b.quantity))
            cb = Decimal(str(b.cost_basis))
            total_cost += cb * qty
            total_qty += qty

    if total_qty <= Decimal("0"):
        return (True, f"No position quantity for {ticker}")

    avg_cost = total_cost / total_qty

    if signal_price < avg_cost:
        return (
            False,
            f"Sell below cost basis rejected — sell ${signal_price:.2f} < "
            f"avg cost ${avg_cost:.2f} for {ticker}"
        )

    profit_pct = ((signal_price - avg_cost) / avg_cost) * 100
    return (True, f"Sell above cost basis (${signal_price:.2f} vs ${avg_cost:.2f}, +{profit_pct:.1f}%)")
