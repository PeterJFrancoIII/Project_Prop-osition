"""
Risk checker — pre-trade risk validation.

Layer 0: Passthrough stub that always approves.
Layer 1: Full implementation with drawdown checks, position limits,
         kill switch enforcement, and prop firm rule compliance.
"""

import logging

logger = logging.getLogger(__name__)


def check_trade(signal: dict, account=None) -> tuple[bool, str]:
    """
    Run pre-trade risk checks on a signal.

    Args:
        signal: Validated signal dict (ticker, action, quantity, etc.).
        account: BrokerAccount instance (optional, used in Layer 1+).

    Returns:
        Tuple of (approved: bool, reason: str).
        - (True, "...") if the trade is approved.
        - (False, "...") if the trade is rejected, with explanation.
    """
    # Layer 0: Passthrough — always approves
    # TODO (Layer 1): Implement full risk checks:
    #   - Check kill switch state
    #   - Check daily drawdown limit
    #   - Check max position size
    #   - Check max open positions
    #   - Check daily trade count
    #   - Check prop firm-specific rules

    logger.info(
        "Risk check PASSED (Layer 0 passthrough): %s %s %s",
        signal.get("action"),
        signal.get("quantity"),
        signal.get("ticker"),
    )
    return (True, "Layer 0 passthrough — full risk checks in Layer 1")
