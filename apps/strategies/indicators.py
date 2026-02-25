"""
Technical indicators for strategy signal generation.

Pure functions operating on lists of OHLCV dicts.
No external dependencies — all calculations are done in Python.
"""

from decimal import Decimal
from typing import Optional


def sma(closes: list[float], period: int) -> list[float]:
    """
    Simple Moving Average.

    Args:
        closes: List of closing prices.
        period: Number of periods for the average.

    Returns:
        List of SMA values (first `period-1` entries are None-padded as 0.0).
    """
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(0.0)
        else:
            window = closes[i - period + 1 : i + 1]
            result.append(sum(window) / period)
    return result


def ema(closes: list[float], period: int) -> list[float]:
    """
    Exponential Moving Average.

    Uses a smoothing factor of 2 / (period + 1).
    """
    if not closes:
        return []

    multiplier = 2.0 / (period + 1)
    result = [closes[0]]  # Seed with first close

    for i in range(1, len(closes)):
        val = (closes[i] * multiplier) + (result[-1] * (1 - multiplier))
        result.append(val)

    return result


def rsi(closes: list[float], period: int = 14) -> list[float]:
    """
    Relative Strength Index (0-100).

    RSI > 70 = overbought, RSI < 30 = oversold.
    """
    if len(closes) < period + 1:
        return [50.0] * len(closes)  # Not enough data — return neutral

    result = [50.0] * period  # Pad initial values as neutral

    # Calculate initial average gain/loss
    gains = []
    losses = []
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - (100.0 / (1.0 + rs)))

    # Calculate remaining values using smoothed method
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = max(change, 0)
        loss = max(-change, 0)

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - (100.0 / (1.0 + rs)))

    return result


def vwap(bars: list[dict]) -> list[float]:
    """
    Volume Weighted Average Price (intraday).

    Resets each day. Uses (high + low + close) / 3 as typical price.

    Args:
        bars: List of OHLCV dicts with high, low, close, volume keys.
    """
    if not bars:
        return []

    result = []
    cum_tp_vol = 0.0
    cum_vol = 0.0

    for bar in bars:
        typical_price = (bar["high"] + bar["low"] + bar["close"]) / 3
        cum_tp_vol += typical_price * bar["volume"]
        cum_vol += bar["volume"]

        if cum_vol > 0:
            result.append(cum_tp_vol / cum_vol)
        else:
            result.append(typical_price)

    return result


def bollinger_bands(
    closes: list[float], period: int = 20, std_devs: float = 2.0
) -> tuple[list[float], list[float], list[float]]:
    """
    Bollinger Bands: middle (SMA), upper (SMA + k*std), lower (SMA - k*std).

    Returns (upper, middle, lower) lists.
    """
    middle = sma(closes, period)
    upper = []
    lower = []

    for i in range(len(closes)):
        if i < period - 1:
            upper.append(0.0)
            lower.append(0.0)
        else:
            window = closes[i - period + 1 : i + 1]
            mean = middle[i]
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance ** 0.5
            upper.append(mean + std_devs * std)
            lower.append(mean - std_devs * std)

    return upper, middle, lower


def zscore(closes: list[float], period: int = 20) -> list[float]:
    """
    Z-Score: how many standard deviations the current price is from the mean.

    Z < -2 = extremely oversold, Z > 2 = extremely overbought.
    """
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(0.0)
        else:
            window = closes[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance ** 0.5
            if std > 0:
                result.append((closes[i] - mean) / std)
            else:
                result.append(0.0)
    return result


def atr(bars: list[dict], period: int = 14) -> list[float]:
    """
    Average True Range — measures volatility.

    Used for stop loss placement and position sizing.
    """
    if len(bars) < 2:
        return [0.0] * len(bars)

    true_ranges = [bars[0]["high"] - bars[0]["low"]]  # First bar: just range

    for i in range(1, len(bars)):
        tr = max(
            bars[i]["high"] - bars[i]["low"],
            abs(bars[i]["high"] - bars[i - 1]["close"]),
            abs(bars[i]["low"] - bars[i - 1]["close"]),
        )
        true_ranges.append(tr)

    # Calculate ATR as SMA of true ranges
    result = []
    for i in range(len(true_ranges)):
        if i < period - 1:
            result.append(0.0)
        else:
            result.append(sum(true_ranges[i - period + 1 : i + 1]) / period)

    return result


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal_period: int = 9
) -> tuple[list[float], list[float], list[float]]:
    """
    MACD (Moving Average Convergence Divergence).

    Returns (macd_line, signal_line, histogram).
    """
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)

    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
    signal_line = ema(macd_line, signal_period)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]

    return macd_line, signal_line, histogram
