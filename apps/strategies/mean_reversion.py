"""
Mean Reversion strategy — buy oversold blue-chips bouncing off support.

Layer 2 stock strategy: uses Bollinger Bands and Z-Score to identify
stocks that have deviated significantly from their mean and are likely
to revert. Buys on extreme oversold conditions, sells on mean recovery.
"""

from decimal import Decimal

from apps.strategies.base import BaseStrategy, Signal
from apps.strategies.indicators import bollinger_bands, zscore, rsi, sma


class MeanReversion(BaseStrategy):
    """
    Mean Reversion — buy oversold stocks expected to revert to the mean.

    Entry conditions (ALL must be true):
      1. Close < Lower Bollinger Band (20, 2σ)  — price at extreme low
      2. Z-Score < -1.5  — statistically oversold
      3. RSI(14) < 35  — momentum confirms oversold
      4. Close > SMA(200)  — only trade stocks in long-term uptrend

    Exit conditions (ANY):
      1. Close > SMA(20) (middle Bollinger Band)  — reverted to mean
      2. RSI > 60  — momentum recovered
      3. Stop loss: 5% below entry (wider stop for mean reversion)
      4. Take profit: 4% above entry
    """

    name = "mean_reversion"
    version = "1.0.0"
    asset_class = "stocks"
    timeframe = "1d"
    description = "Buy oversold blue-chips bouncing off Bollinger Band support"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.bb_period = self.config.get("bb_period", 20)
        self.bb_std = self.config.get("bb_std_devs", 2.0)
        self.zscore_threshold = self.config.get("zscore_threshold", -1.5)
        self.rsi_entry = self.config.get("rsi_entry_threshold", 35)
        self.rsi_exit = self.config.get("rsi_exit_threshold", 60)
        self.sma_trend_period = self.config.get("sma_trend_period", 200)
        self.stop_loss_pct = Decimal(str(self.config.get("stop_loss_pct", 5.0)))
        self.take_profit_pct = Decimal(str(self.config.get("take_profit_pct", 4.0)))

    def generate_signal(self, ticker: str, bars: list) -> Signal:
        if len(bars) < self.sma_trend_period:
            return Signal(Signal.HOLD, ticker, reason="Not enough data for SMA200", strategy_name=self.name)

        closes = [b["close"] for b in bars]

        # Calculate indicators
        upper, middle, lower = bollinger_bands(closes, self.bb_period, self.bb_std)
        z_values = zscore(closes, self.bb_period)
        rsi_values = rsi(closes)
        sma200 = sma(closes, self.sma_trend_period)

        current_close = closes[-1]
        current_lower_bb = lower[-1]
        current_z = z_values[-1]
        current_rsi = rsi_values[-1]
        current_sma200 = sma200[-1]

        # --- Entry conditions ---
        below_lower_bb = current_close < current_lower_bb
        zscore_oversold = current_z < self.zscore_threshold
        rsi_oversold = current_rsi < self.rsi_entry
        in_uptrend = current_close > current_sma200

        if below_lower_bb and zscore_oversold and rsi_oversold and in_uptrend:
            return Signal(
                action=Signal.BUY,
                ticker=ticker,
                price=Decimal(str(current_close)),
                confidence=min(abs(current_z) / 3.0, 0.95),
                reason=f"Mean reversion: Z={current_z:.2f}, RSI={current_rsi:.1f}, "
                       f"close ${current_close:.2f} < BB lower ${current_lower_bb:.2f}",
                strategy_name=self.name,
            )

        return Signal(Signal.HOLD, ticker, reason="No mean reversion signal", strategy_name=self.name)

    def calculate_position_size(self, ticker: str, price: Decimal, account_equity: Decimal) -> Decimal:
        risk_pct = Decimal(str(self.config.get("risk_per_trade_pct", 1.5)))
        risk_amount = account_equity * risk_pct / Decimal("100")
        stop_distance = price * self.stop_loss_pct / Decimal("100")

        if stop_distance <= 0:
            return Decimal("1")

        shares = risk_amount / stop_distance
        return max(Decimal("1"), shares.quantize(Decimal("1")))

    def check_exit(self, ticker: str, entry_price: Decimal, current_price: Decimal, bars: list) -> Signal:
        if not bars:
            return Signal(Signal.HOLD, ticker, strategy_name=self.name)

        closes = [b["close"] for b in bars]

        # Stop loss (wider for mean reversion)
        loss_pct = (entry_price - current_price) / entry_price * Decimal("100")
        if loss_pct >= self.stop_loss_pct:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"Stop loss: -{loss_pct:.1f}% (limit: {self.stop_loss_pct}%)",
                strategy_name=self.name,
            )

        # Take profit
        gain_pct = (current_price - entry_price) / entry_price * Decimal("100")
        if gain_pct >= self.take_profit_pct:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"Take profit: +{gain_pct:.1f}%",
                strategy_name=self.name,
            )

        # Mean reverted — close above SMA20
        sma_values = sma(closes, self.bb_period)
        if closes[-1] > sma_values[-1] and sma_values[-1] > 0:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"Mean reverted: close ${closes[-1]:.2f} > SMA20 ${sma_values[-1]:.2f}",
                strategy_name=self.name,
            )

        # RSI recovered
        rsi_values = rsi(closes)
        if rsi_values[-1] > self.rsi_exit:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"RSI recovered: {rsi_values[-1]:.1f} > {self.rsi_exit}",
                strategy_name=self.name,
            )

        return Signal(Signal.HOLD, ticker, strategy_name=self.name)
