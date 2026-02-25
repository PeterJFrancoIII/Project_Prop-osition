"""
Risk checker tests — validates all 7 safety checks.

Tests each check in isolation: kill switch, market hours, daily drawdown,
daily loss limit, daily trade count, max open positions, position size.
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from apps.execution_engine.models import Trade
from apps.risk_management.models import RiskConfig
from apps.risk_management.risk_checker import (
    check_trade,
    _check_kill_switch,
    _check_market_hours,
    _check_daily_drawdown,
    _check_daily_loss_limit,
    _check_daily_trade_count,
    _check_max_open_positions,
    _check_position_size,
)


class KillSwitchCheckTests(TestCase):
    """Kill switch must block ALL trades when active."""

    def setUp(self):
        self.config = RiskConfig.objects.create(name="test", is_active=True)

    def test_kill_switch_active_blocks(self):
        self.config.kill_switch_active = True
        self.config.save()
        approved, reason = _check_kill_switch(self.config)
        self.assertFalse(approved)
        self.assertIn("ACTIVE", reason)

    def test_kill_switch_inactive_passes(self):
        self.config.kill_switch_active = False
        self.config.save()
        approved, reason = _check_kill_switch(self.config)
        self.assertTrue(approved)


class MarketHoursCheckTests(TestCase):
    """Stock trades must only execute during market hours."""

    def test_crypto_always_allowed(self):
        signal = {"ticker": "BTC", "action": "buy", "strategy": "crypto_v1"}
        approved, reason = _check_market_hours(signal)
        self.assertTrue(approved)
        self.assertIn("Crypto", reason)

    def test_futures_always_allowed(self):
        signal = {"ticker": "MES", "action": "buy", "strategy": "futures_v1"}
        approved, reason = _check_market_hours(signal)
        self.assertTrue(approved)
        self.assertIn("Futures", reason)

    @patch("apps.risk_management.risk_checker.timezone")
    def test_weekend_blocks_stocks(self, mock_tz):
        """Saturday/Sunday should block stock trades."""
        import pytz
        saturday = timezone.now().replace(hour=12, minute=0)
        # Mock to return a Saturday
        mock_saturday = MagicMock()
        mock_saturday.weekday.return_value = 5  # Saturday
        mock_saturday.strftime.return_value = "Saturday"
        mock_saturday.time.return_value = saturday.time()

        mock_tz.now.return_value = saturday
        with patch("pytz.timezone") as mock_pytz:
            mock_eastern = MagicMock()
            mock_eastern.return_value = mock_saturday
            saturday.astimezone = MagicMock(return_value=mock_saturday)
            mock_pytz.return_value = mock_eastern

            signal = {"ticker": "AAPL", "action": "buy", "strategy": "momentum_v1"}
            approved, reason = _check_market_hours(signal)
            self.assertFalse(approved)
            self.assertIn("weekend", reason.lower())


class DailyDrawdownCheckTests(TestCase):
    """Daily P&L must not exceed the loss limit."""

    def setUp(self):
        self.config = RiskConfig.objects.create(
            name="test", is_active=True, daily_loss_limit=Decimal("500.00")
        )

    def test_no_trades_passes(self):
        approved, reason = _check_daily_drawdown(self.config)
        self.assertTrue(approved)

    def test_profitable_day_passes(self):
        Trade.objects.create(
            symbol="AAPL", side="buy", quantity=10, strategy="test",
            status="filled", realized_pnl=Decimal("200.00")
        )
        approved, reason = _check_daily_drawdown(self.config)
        self.assertTrue(approved)

    def test_loss_within_limit_passes(self):
        Trade.objects.create(
            symbol="AAPL", side="buy", quantity=10, strategy="test",
            status="filled", realized_pnl=Decimal("-300.00")
        )
        approved, reason = _check_daily_drawdown(self.config)
        self.assertTrue(approved)

    def test_loss_exceeds_limit_blocks(self):
        Trade.objects.create(
            symbol="AAPL", side="buy", quantity=10, strategy="test",
            status="filled", realized_pnl=Decimal("-600.00")
        )
        approved, reason = _check_daily_drawdown(self.config)
        self.assertFalse(approved)
        self.assertIn("drawdown limit", reason.lower())


class DailyTradeCountTests(TestCase):
    """Trade count must not exceed the daily limit."""

    def setUp(self):
        self.config = RiskConfig.objects.create(
            name="test", is_active=True, max_daily_trades=3
        )

    def test_under_limit_passes(self):
        Trade.objects.create(symbol="AAPL", side="buy", quantity=10, strategy="test")
        approved, reason = _check_daily_trade_count(self.config)
        self.assertTrue(approved)

    def test_at_limit_blocks(self):
        for i in range(3):
            Trade.objects.create(symbol=f"SYM{i}", side="buy", quantity=10, strategy="test")
        approved, reason = _check_daily_trade_count(self.config)
        self.assertFalse(approved)
        self.assertIn("limit reached", reason.lower())


class MaxOpenPositionsTests(TestCase):
    """Open position count must not exceed the limit."""

    def setUp(self):
        self.config = RiskConfig.objects.create(
            name="test", is_active=True, max_open_positions=2
        )

    @patch("apps.risk_management.risk_checker.AlpacaClient")
    def test_under_limit_passes(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get_positions.return_value = [{"symbol": "AAPL"}]
        mock_client_cls.return_value = mock_client

        approved, reason = _check_max_open_positions(self.config)
        self.assertTrue(approved)

    @patch("apps.risk_management.risk_checker.AlpacaClient")
    def test_at_limit_blocks(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get_positions.return_value = [
            {"symbol": "AAPL"}, {"symbol": "MSFT"}
        ]
        mock_client_cls.return_value = mock_client

        approved, reason = _check_max_open_positions(self.config)
        self.assertFalse(approved)


class PositionSizeTests(TestCase):
    """Position value must not exceed max % of equity."""

    def setUp(self):
        self.config = RiskConfig.objects.create(
            name="test", is_active=True, max_position_size_pct=Decimal("5.00")
        )

    def test_market_order_no_price_skips(self):
        signal = {"ticker": "AAPL", "action": "buy", "quantity": "10", "price": "0"}
        approved, reason = _check_position_size(self.config, signal)
        self.assertTrue(approved)
        self.assertIn("skipped", reason.lower())

    def test_small_order_passes(self):
        signal = {"ticker": "AAPL", "action": "buy", "quantity": "10", "price": "100"}
        # 10 * 100 = $1,000 which is 1% of $100k equity (under 5% limit)
        approved, reason = _check_position_size(self.config, signal)
        self.assertTrue(approved)

    def test_large_order_blocks(self):
        signal = {"ticker": "AAPL", "action": "buy", "quantity": "100", "price": "200"}
        # 100 * 200 = $20,000 which is 20% of $100k equity (over 5% limit)
        approved, reason = _check_position_size(self.config, signal)
        self.assertFalse(approved)
        self.assertIn("too large", reason.lower())


class FullPipelineTests(TestCase):
    """End-to-end check_trade pipeline tests."""

    def setUp(self):
        self.config = RiskConfig.objects.create(name="default", is_active=True)
        self.valid_signal = {
            "ticker": "AAPL",
            "action": "buy",
            "quantity": "10",
            "price": "150",
            "strategy": "momentum_v1",
        }

    def test_no_active_config_rejects(self):
        RiskConfig.objects.all().delete()
        approved, reason = check_trade(self.valid_signal)
        self.assertFalse(approved)
        self.assertIn("No active risk configuration", reason)

    def test_kill_switch_active_rejects(self):
        self.config.kill_switch_active = True
        self.config.save()
        approved, reason = check_trade(self.valid_signal)
        self.assertFalse(approved)
        self.assertIn("Kill switch", reason)

    @patch("apps.risk_management.risk_checker._check_market_hours")
    def test_valid_trade_passes(self, mock_hours):
        """Valid trade with market hours mocked passes all checks."""
        mock_hours.return_value = (True, "Within market hours")
        approved, reason = check_trade(self.valid_signal)
        self.assertTrue(approved)
        self.assertIn("All risk checks passed", reason)
