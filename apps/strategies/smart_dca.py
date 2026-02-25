"""
Smart DCA strategy — accumulates long-term positions by buying dips.

Layer 2 stock strategy: buys when price is below SMA50 or RSI is oversold.
Never sells (strictly for accumulation/long-term holds).
"""

from decimal import Decimal

from apps.strategies.base import BaseStrategy, Signal
from apps.strategies.indicators import sma, rsi


class SmartDCA(BaseStrategy):
    """
    Smart DCA — dollar-cost averaging enhanced by buying the dip.

    Entry conditions (ANY must be true):
      1. Close < SMA(50)  — price has dipped below short-term trend
      2. RSI(14) < 40  — short-term momentum is oversold

    Exit conditions:
      - None (always HOLD). Strategy builder or manual intervention required to exit.
    """

    name = "smart_dca"
    version = "1.0.0"
    asset_class = "stocks"
    timeframe = "1d"
    description = "Accumulate positions on dips (Price < SMA50 or RSI < 40)"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.sma_period = self.config.get("sma_period", 50)
        self.rsi_period = self.config.get("rsi_period", 14)
        self.rsi_threshold = self.config.get("rsi_threshold", 40)
        self.dca_amount = Decimal(str(self.config.get("dca_amount", 500.0)))
        
        # Unused by DCA but required by some runner logic if they check it
        self.stop_loss_pct = Decimal("100.0")
        self.take_profit_pct = Decimal("1000.0")

    def generate_signal(self, ticker: str, bars: list) -> Signal:
        if len(bars) < max(self.sma_period, self.rsi_period) + 1:
            return Signal(Signal.HOLD, ticker, reason="Not enough data", strategy_name=self.name)

        closes = [b["close"] for b in bars]

        # Calculate indicators
        sma_values = sma(closes, self.sma_period)
        rsi_values = rsi(closes, self.rsi_period)

        current_close = closes[-1]
        current_sma = sma_values[-1]
        current_rsi = rsi_values[-1]

        # --- Entry conditions ---
        below_sma = current_close < current_sma
        is_oversold = current_rsi < self.rsi_threshold

        if below_sma or is_oversold:
            reason = []
            if below_sma:
                reason.append(f"Close ${current_close:.2f} < SMA50 ${current_sma:.2f}")
            if is_oversold:
                reason.append(f"RSI({self.rsi_period}) {current_rsi:.1f} < {self.rsi_threshold}")

            return Signal(
                action=Signal.BUY,
                ticker=ticker,
                price=Decimal(str(current_close)),
                confidence=min((100 - current_rsi) / 100.0, 0.95),  # Lower RSI = higher confidence
                reason="Smart DCA Dip: " + " AND ".join(reason),
                strategy_name=self.name,
            )

        return Signal(Signal.HOLD, ticker, reason="Price is elevated, waiting for dip", strategy_name=self.name)

    def calculate_position_size(self, ticker: str, price: Decimal, account_equity: Decimal) -> Decimal:
        if price <= 0:
            return Decimal("1")
            
        buy_amount = self.dca_amount
        
        # Don't spend more than we have (plus a tiny buffer)
        if buy_amount > account_equity:
            buy_amount = account_equity * Decimal("0.95")

        if buy_amount < price:
            return Decimal("0") # Can't afford 1 share

        shares = buy_amount / price
        return max(Decimal("1"), shares.quantize(Decimal("1")))

    def check_exit(self, ticker: str, entry_price: Decimal, current_price: Decimal, bars: list) -> Signal:
        # Smart DCA never exits automatically.
        return Signal(Signal.HOLD, ticker, strategy_name=self.name)
