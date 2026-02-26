"""
Signal executor — the core trade execution pipeline.

Receives validated signals from the webhook receiver, runs risk checks,
routes to the appropriate broker, and logs the result.
Layer 1: Includes cost basis tracking and realized P&L calculation.
"""

import logging
from decimal import Decimal

from django.db.models import Sum, F

from apps.execution_engine.models import Trade
from apps.risk_management.risk_checker import check_trade
from apps.broker_connector.ib_routing import IBRoutingBroker
from apps.dashboard.models import Strategy
from apps.risk_management.prop_firm_models import PropFirmAccount

logger = logging.getLogger(__name__)


def execute_signal(signal: dict) -> list[Trade]:
    """
    Execute a validated trade signal via Block Trading (Order Batching).

    Pipeline:
      1. Lookup prop accounts attached to the strategy.
      2. Run Risk checks for each account.
      3. Sum the allocated portions for approved accounts to form ONE massive block order.
      4. Submit the single Block Order to the Master Broker API.
      5. Create perfectly synchronized Trade records for each approved account using the master fill price.

    Args:
        signal: Validated signal dict.
        
    Returns:
        List of Trade objects.
    """
    strategy_name = signal.get("strategy")
    strategy_obj = Strategy.objects.filter(name=strategy_name).first()
    
    accounts = []
    if strategy_obj and strategy_obj.is_active and strategy_obj.account_numbers:
        acct_list = [x.strip() for x in strategy_obj.account_numbers.split(",") if x.strip()]
        if acct_list:
            accounts = list(PropFirmAccount.objects.filter(
                account_number__in=acct_list,
                is_active=True
            ))
        
    if not accounts:
        # Fallback to no-account (default Alpaca Master)
        accounts = [None]
        
    approved_accounts = []
    rejected_trades = []
    
    # 1. Run local Risk checks for all accounts individually
    for account in accounts:
        approved, reason = check_trade(signal, account=account)
        if not approved:
            # Create a rejected trade stub for the ledger
            t = Trade.objects.create(
                symbol=signal["ticker"],
                side=signal["action"],
                quantity=Decimal("0"),
                strategy=strategy_name,
                status="rejected",
                error_message=reason,
                broker_account_id=account.account_number if account else "",
                risk_approved=False,
                risk_reason=reason
            )
            rejected_trades.append(t)
            logger.warning("Trade rejected for %s: %s", t.broker_account_id, reason)
        else:
            approved_accounts.append(account)
            
    if not approved_accounts:
        logger.warning(f"Block Trade aborted for {strategy_name}: All accounts failed risk check.")
        return rejected_trades

    # 2. Calculate the block size
    # By default, the Strategy Runner calculates an aggregated baseline `qty` based on the master 
    # portfolio allocator. We apply that master quantity to the total block order.
    total_quantity = Decimal(str(signal["quantity"]))
    
    # 3. Submit Master Block Order to the Broker
    # Smart slippage control: prevent massive bad fills
    order_type = "market"
    limit_price = None
    intended_price = float(signal.get("price") or 0)
    
    if intended_price > 0:
        if signal["action"] == "buy":
            order_type = "limit"
            limit_price = float(Decimal(str(intended_price)) * Decimal("1.01"))
        elif signal["action"] == "sell":
            if "panic" in signal.get("reason", "").lower() or "stop" in signal.get("reason", "").lower():
                order_type = "market"
            else:
                order_type = "limit"
                limit_price = float(Decimal(str(intended_price)) * Decimal("0.99"))

    master_fill_price = None
    master_broker_id = ""
    status = "pending"
    error_message = ""
    
    try:
        # Use IB Gateway logic to submit the massive block trade
        client = IBRoutingBroker()
        order_result = client.submit_block_order(
            strategy_name=strategy_name or "UNKNOWN",
            symbol=signal["ticker"],
            qty=float(total_quantity),
            side=signal["action"],
            order_type=order_type,
            time_in_force="day",
            limit_price=limit_price,
            stop_price=None  # Can add stop price logic if needed
        )
        
        master_broker_id = order_result.get("order_id", "")
        status = "submitted"
        if order_result.get("filled_avg_price"):
            master_fill_price = Decimal(str(order_result["filled_avg_price"]))
            status = "filled"
            
    except Exception as e:
        status = "error"
        error_message = str(e)
        logger.error(f"Master Block Trade Failed: {e}", exc_info=True)

    # 4. Distribute the Master Trade into localized Account ledgers
    final_trades = rejected_trades
    
    # Prorate the total quantity across approved accounts based on equity weightings
    total_approved_equity: Decimal = Decimal("0")
    for a in approved_accounts:
        if isinstance(a, PropFirmAccount):
            total_approved_equity += Decimal(str(a.current_equity))
            
    if total_approved_equity <= Decimal("0"):
        total_approved_equity = Decimal("100")
    
    for account in approved_accounts:
        # Determine fractional quantity for this account
        if not isinstance(account, PropFirmAccount):
            acct_qty = total_quantity
        else:
            weight = Decimal(str(account.current_equity)) / total_approved_equity
            acct_qty = total_quantity * weight
            
        trade = Trade.objects.create(
            symbol=signal["ticker"],
            side=signal["action"],
            quantity=acct_qty,
            requested_price=Decimal(str(intended_price)) if intended_price else None,
            strategy=strategy_name,
            status=status,
            broker_account_id=account.account_number if account else "",
            broker_order_id=master_broker_id,
            error_message=error_message,
            risk_approved=True,
            risk_reason="Passed Block Check"
        )
        
        if status == "filled" and master_fill_price:
            trade.fill_price = master_fill_price
            _update_cost_basis(trade)
            trade.save()
            
        final_trades.append(trade)
        
    return final_trades


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
        symbol=symbol, side="buy", status="filled"
    )

    total_cost: Decimal = Decimal("0")
    total_qty: Decimal = Decimal("0")

    for b in buys:
        if b.cost_basis is not None and Decimal(str(b.cost_basis)) > 0:
            qty = Decimal(str(b.quantity))
            cb = Decimal(str(b.cost_basis))
            cost_add: Decimal = cb * qty
            total_cost += cost_add
            total_qty += qty

    if total_qty > Decimal("0"):
        result: Decimal = total_cost / total_qty
        return result

    return None
