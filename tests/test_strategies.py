"""
Tests for technical indicators and strategy framework.

Tests indicators for mathematical correctness and strategies
for proper signal generation.
"""

from decimal import Decimal

from django.test import TestCase

from apps.strategies.indicators import sma, ema, rsi, bollinger_bands, zscore, atr, macd, vwap
from apps.strategies.base import Signal
from apps.strategies.momentum_breakout import MomentumBreakout
from apps.strategies.mean_reversion import MeanReversion


# ──────────────────────────────────────────────
# Technical Indicator Tests
# ──────────────────────────────────────────────

class SMATests(TestCase):
    """Simple Moving Average correctness."""

    def test_sma_basic(self):
        closes = [10, 20, 30, 40, 50]
        result = sma(closes, 3)
        self.assertAlmostEqual(result[2], 20.0)  # (10+20+30)/3
        self.assertAlmostEqual(result[3], 30.0)  # (20+30+40)/3
        self.assertAlmostEqual(result[4], 40.0)  # (30+40+50)/3

    def test_sma_padding(self):
        result = sma([1, 2, 3, 4, 5], 3)
        self.assertEqual(result[0], 0.0)
        self.assertEqual(result[1], 0.0)


class EMATests(TestCase):
    """Exponential Moving Average correctness."""

    def test_ema_first_value_equals_close(self):
        result = ema([100, 110, 120], 3)
        self.assertEqual(result[0], 100)

    def test_ema_responds_to_price(self):
        result = ema([100, 200, 200, 200, 200], 3)
        # EMA should approach 200 as price stays at 200
        self.assertGreater(result[-1], result[1])


class RSITests(TestCase):
    """Relative Strength Index correctness."""

    def test_rsi_range(self):
        """RSI must always be between 0 and 100."""
        closes = list(range(100, 150)) + list(range(150, 100, -1))
        result = rsi(closes)
        for v in result:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 100.0)

    def test_rsi_uptrend_high(self):
        """Strong uptrend should produce RSI > 50."""
        closes = list(range(100, 130))
        result = rsi(closes)
        self.assertGreater(result[-1], 50)

    def test_rsi_downtrend_low(self):
        """Strong downtrend should produce RSI < 50."""
        closes = list(range(130, 100, -1))
        result = rsi(closes)
        self.assertLess(result[-1], 50)


class BollingerBandsTests(TestCase):
    """Bollinger Bands correctness."""

    def test_upper_above_lower(self):
        """Upper band must always be >= lower band."""
        closes = [100 + i % 10 for i in range(50)]
        upper, middle, lower = bollinger_bands(closes, 20)
        for i in range(20, len(closes)):
            self.assertGreaterEqual(upper[i], lower[i])

    def test_middle_is_sma(self):
        """Middle band should equal SMA."""
        closes = [float(x) for x in range(100, 125)]
        upper, middle, lower = bollinger_bands(closes, 5)
        sma_vals = sma(closes, 5)
        for i in range(5, len(closes)):
            self.assertAlmostEqual(middle[i], sma_vals[i], places=5)


class ZScoreTests(TestCase):
    """Z-Score correctness."""

    def test_stable_price_zscore_near_zero(self):
        """Stable price should give Z-Score near 0."""
        closes = [100.0] * 30
        result = zscore(closes, 20)
        self.assertAlmostEqual(result[-1], 0.0)


class ATRTests(TestCase):
    """Average True Range correctness."""

    def test_atr_positive(self):
        """ATR should always be positive."""
        bars = [
            {"high": 110 + i, "low": 100 + i, "close": 105 + i}
            for i in range(20)
        ]
        result = atr(bars)
        for v in result[14:]:
            self.assertGreater(v, 0)


class MACDTests(TestCase):
    """MACD correctness."""

    def test_macd_three_outputs(self):
        """MACD should return macd_line, signal_line, histogram."""
        closes = list(range(100, 140))
        macd_line, signal_line, histogram = macd(closes)
        self.assertEqual(len(macd_line), len(closes))
        self.assertEqual(len(signal_line), len(closes))
        self.assertEqual(len(histogram), len(closes))


class VWAPTests(TestCase):
    """VWAP correctness."""

    def test_vwap_single_bar(self):
        bars = [{"high": 110, "low": 100, "close": 105, "volume": 1000}]
        result = vwap(bars)
        expected = (110 + 100 + 105) / 3  # Typical price
        self.assertAlmostEqual(result[0], expected)


# ──────────────────────────────────────────────
# Strategy Tests
# ──────────────────────────────────────────────

class SignalTests(TestCase):
    """Signal data class tests."""

    def test_buy_is_actionable(self):
        s = Signal(Signal.BUY, "AAPL")
        self.assertTrue(s.is_actionable)

    def test_hold_not_actionable(self):
        s = Signal(Signal.HOLD, "AAPL")
        self.assertFalse(s.is_actionable)

    def test_to_dict_format(self):
        s = Signal(Signal.BUY, "AAPL", Decimal("10"), Decimal("150"), 0.8, "test", "momentum")
        d = s.to_dict()
        self.assertEqual(d["ticker"], "AAPL")
        self.assertEqual(d["action"], "buy")
        self.assertEqual(d["quantity"], "10")
        self.assertEqual(d["strategy"], "momentum")


class MomentumBreakoutTests(TestCase):
    """Momentum Breakout strategy logic tests."""

    def setUp(self):
        self.strategy = MomentumBreakout()

    def test_not_enough_data_holds(self):
        bars = [{"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000}] * 10
        signal = self.strategy.generate_signal("AAPL", bars)
        self.assertEqual(signal.action, Signal.HOLD)
        self.assertIn("Not enough data", signal.reason)

    def test_position_size_calculation(self):
        qty = self.strategy.calculate_position_size("AAPL", Decimal("150"), Decimal("100000"))
        self.assertGreater(qty, 0)
        self.assertIsInstance(qty, Decimal)

    def test_stop_loss_exit(self):
        """Price dropping below stop loss should trigger sell."""
        bars = [{"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000}] * 20
        signal = self.strategy.check_exit(
            "AAPL", Decimal("100"), Decimal("95"), bars
        )
        self.assertEqual(signal.action, Signal.SELL)
        self.assertIn("Stop loss", signal.reason)

    def test_take_profit_exit(self):
        """Price reaching take profit should trigger sell."""
        bars = [{"open": 100, "high": 115, "low": 100, "close": 110, "volume": 1000}] * 20
        signal = self.strategy.check_exit(
            "AAPL", Decimal("100"), Decimal("107"), bars
        )
        self.assertEqual(signal.action, Signal.SELL)
        self.assertIn("Take profit", signal.reason)


class MeanReversionTests(TestCase):
    """Mean Reversion strategy logic tests."""

    def setUp(self):
        self.strategy = MeanReversion()

    def test_not_enough_data_holds(self):
        bars = [{"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000}] * 50
        signal = self.strategy.generate_signal("AAPL", bars)
        self.assertEqual(signal.action, Signal.HOLD)
        self.assertIn("Not enough data", signal.reason)

    def test_position_size_calculation(self):
        qty = self.strategy.calculate_position_size("AAPL", Decimal("50"), Decimal("100000"))
        self.assertGreater(qty, 0)

    def test_stop_loss_exit(self):
        bars = [{"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000}] * 25
        signal = self.strategy.check_exit(
            "AAPL", Decimal("100"), Decimal("93"), bars
        )
        self.assertEqual(signal.action, Signal.SELL)
        self.assertIn("Stop loss", signal.reason)
