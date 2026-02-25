"""
Sector Rotation strategy — buy strong sectors based on momentum and trend.

Layer 2 stock strategy: scans for positive Rate of Change (ROC) in a long-term
uptrend (price > SMA200). Sells when the trend or momentum breaks.
"""

from decimal import Decimal

from apps.strategies.base import BaseStrategy, Signal
from apps.strategies.indicators import sma, roc


class SectorRotation(BaseStrategy):
    """
    Sector Rotation — buy strong momentum stocks in an uptrend.

    Entry conditions (ALL must be true):
      1. Close > SMA(200)  — long term trend is up
      2. ROC(90) > minimum threshold (e.g. 5%)  — strong medium-term momentum

    Exit conditions (ANY):
      1. Close < SMA(200)  — trend broken
      2. ROC(90) < 0  — momentum turns negative
      3. Stop loss hit
      4. Take profit hit
    """

    name = "sector_rotation"
    version = "1.0.0"
    asset_class = "stocks"
    timeframe = "1d"
    description = "Buy stocks with strong medium-term momentum in a long-term uptrend"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.roc_period = self.config.get("roc_period", 90)
        self.roc_entry_threshold = self.config.get("roc_entry_threshold", 5.0)
        self.sma_trend_period = self.config.get("sma_trend_period", 200)
        self.stop_loss_pct = Decimal(str(self.config.get("stop_loss_pct", 8.0)))
        self.take_profit_pct = Decimal(str(self.config.get("take_profit_pct", 15.0)))

    def generate_signal(self, ticker: str, bars: list) -> Signal:
        if len(bars) < max(self.sma_trend_period, self.roc_period) + 1:
            return Signal(Signal.HOLD, ticker, reason="Not enough data", strategy_name=self.name)

        closes = [b["close"] for b in bars]

        # Calculate indicators
        sma_values = sma(closes, self.sma_trend_period)
        roc_values = roc(closes, self.roc_period)

        current_close = closes[-1]
        current_sma200 = sma_values[-1]
        current_roc = roc_values[-1]

        # --- Entry conditions ---
        in_uptrend = current_close > current_sma200
        strong_momentum = current_roc > self.roc_entry_threshold

        if in_uptrend and strong_momentum:
            return Signal(
                action=Signal.BUY,
                ticker=ticker,
                price=Decimal(str(current_close)),
                confidence=min(current_roc / 20.0, 0.95),  # 20% ROC = ~95% confidence
                reason=f"Sector Rotation: ROC({self.roc_period}) is {current_roc:.2f}% > {self.roc_entry_threshold}%, "
                       f"Close ${current_close:.2f} > SMA200 ${current_sma200:.2f}",
                strategy_name=self.name,
            )

        return Signal(Signal.HOLD, ticker, reason="No momentum rotation signal", strategy_name=self.name)

    def calculate_position_size(self, ticker: str, price: Decimal, account_equity: Decimal) -> Decimal:
        num_sectors = Decimal(str(self.config.get("target_sectors", 5)))
        target_allocation = account_equity / num_sectors

        if price <= 0:
            return Decimal("1")

        shares = target_allocation / price
        return max(Decimal("1"), shares.quantize(Decimal("1")))

    def check_exit(self, ticker: str, entry_price: Decimal, current_price: Decimal, bars: list) -> Signal:
        if not bars:
            return Signal(Signal.HOLD, ticker, strategy_name=self.name)

        closes = [b["close"] for b in bars]

        # Stop loss
        loss_pct = (entry_price - current_price) / entry_price * Decimal("100")
        if loss_pct >= self.stop_loss_pct:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"Stop loss hit: -{loss_pct:.1f}% (limit: {self.stop_loss_pct}%)",
                strategy_name=self.name,
            )

        # Take profit
        gain_pct = (current_price - entry_price) / entry_price * Decimal("100")
        if gain_pct >= self.take_profit_pct:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"Take profit hit: +{gain_pct:.1f}% (limit: {self.take_profit_pct}%)",
                strategy_name=self.name,
            )

        # Trend broken
        sma_values = sma(closes, self.sma_trend_period)
        if closes[-1] < sma_values[-1] and sma_values[-1] > 0:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"Trend broken: close ${closes[-1]:.2f} < SMA200 ${sma_values[-1]:.2f}",
                strategy_name=self.name,
            )

        # Momentum lost
        roc_values = roc(closes, self.roc_period)
        if roc_values[-1] < 0:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"Momentum lost: ROC({self.roc_period}) is negative ({roc_values[-1]:.2f}%)",
                strategy_name=self.name,
            )

        return Signal(Signal.HOLD, ticker, strategy_name=self.name)
