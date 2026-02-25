"""
Momentum Breakout strategy — buy stocks breaking out above resistance on volume.

Layer 2 stock strategy: scans for price above SMA20 + RSI confirmation + volume surge.
Sells when RSI overbought or price drops below EMA9.
"""

from decimal import Decimal

from apps.strategies.base import BaseStrategy, Signal
from apps.strategies.indicators import rsi, sma, ema, atr


class MomentumBreakout(BaseStrategy):
    """
    Momentum Breakout — buy on breakout above SMA with volume confirmation.

    Entry conditions (ALL must be true):
      1. Close > SMA(20)  — price above trend
      2. RSI(14) between 40-70  — momentum building, not overbought
      3. Volume > 1.5× AVG(20) volume  — surge confirms breakout
      4. Close > prior day's high  — breakout above resistance

    Exit conditions (ANY):
      1. RSI(14) > 80  — overbought
      2. Close < EMA(9)  — trend reversal
      3. Stop loss hit (configurable, default 3%)
      4. Take profit hit (configurable, default 6%)
    """

    name = "momentum_breakout"
    version = "1.0.0"
    asset_class = "stocks"
    timeframe = "1d"
    description = "Buy stocks breaking out above resistance with volume confirmation"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.sma_period = self.config.get("sma_period", 20)
        self.rsi_period = self.config.get("rsi_period", 14)
        self.volume_multiplier = self.config.get("volume_multiplier", 1.5)
        self.rsi_entry_low = self.config.get("rsi_entry_low", 40)
        self.rsi_entry_high = self.config.get("rsi_entry_high", 70)
        self.rsi_exit_overbought = self.config.get("rsi_exit_overbought", 80)
        self.stop_loss_pct = Decimal(str(self.config.get("stop_loss_pct", 3.0)))
        self.take_profit_pct = Decimal(str(self.config.get("take_profit_pct", 6.0)))

    def generate_signal(self, ticker: str, bars: list) -> Signal:
        if len(bars) < self.sma_period + 1:
            return Signal(Signal.HOLD, ticker, reason="Not enough data", strategy_name=self.name)

        closes = [b["close"] for b in bars]
        volumes = [b["volume"] for b in bars]

        # Calculate indicators
        sma_values = sma(closes, self.sma_period)
        rsi_values = rsi(closes, self.rsi_period)

        # Average volume over lookback
        avg_volume = sum(volumes[-self.sma_period:]) / self.sma_period

        current_close = closes[-1]
        current_rsi = rsi_values[-1]
        current_sma = sma_values[-1]
        current_vol = volumes[-1]
        prior_high = bars[-2]["high"] if len(bars) > 1 else 0

        # --- Entry conditions ---
        above_sma = current_close > current_sma
        rsi_in_range = self.rsi_entry_low <= current_rsi <= self.rsi_entry_high
        volume_surge = current_vol > avg_volume * self.volume_multiplier
        breakout = current_close > prior_high

        if above_sma and rsi_in_range and volume_surge and breakout:
            return Signal(
                action=Signal.BUY,
                ticker=ticker,
                price=Decimal(str(current_close)),
                confidence=min(current_rsi / 100, 0.95),
                reason=f"Breakout: close ${current_close:.2f} > SMA20 ${current_sma:.2f}, "
                       f"RSI {current_rsi:.1f}, vol {current_vol/avg_volume:.1f}x avg",
                strategy_name=self.name,
            )

        return Signal(Signal.HOLD, ticker, reason="No breakout signal", strategy_name=self.name)

    def calculate_position_size(self, ticker: str, price: Decimal, account_equity: Decimal) -> Decimal:
        risk_pct = Decimal(str(self.config.get("risk_per_trade_pct", 2.0)))
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
                reason=f"Take profit hit: +{gain_pct:.1f}% (target: {self.take_profit_pct}%)",
                strategy_name=self.name,
            )

        # RSI overbought exit
        rsi_values = rsi(closes, self.rsi_period)
        if rsi_values[-1] > self.rsi_exit_overbought:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"RSI overbought: {rsi_values[-1]:.1f} > {self.rsi_exit_overbought}",
                strategy_name=self.name,
            )

        # EMA cross-under exit
        ema_values = ema(closes, 9)
        if closes[-1] < ema_values[-1]:
            return Signal(
                Signal.SELL, ticker, price=current_price,
                reason=f"Price ${closes[-1]:.2f} below EMA9 ${ema_values[-1]:.2f}",
                strategy_name=self.name,
            )

        return Signal(Signal.HOLD, ticker, strategy_name=self.name)
