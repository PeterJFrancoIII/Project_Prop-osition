"""
Integration test — full pipeline: webhook → risk check → execute.

Tests the complete trade execution flow end-to-end,
mocking only the Alpaca broker interaction.
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.execution_engine.executor import execute_signal
from apps.execution_engine.models import Trade
from apps.risk_management.models import RiskConfig


class IntegrationPipelineTests(TestCase):
    """End-to-end: signal → risk → broker → trade with cost basis."""

    def setUp(self):
        self.config = RiskConfig.objects.create(
            name="default", is_active=True,
            max_daily_drawdown_pct=Decimal("5.00"),
            max_daily_trades=50,
            max_open_positions=10,
            max_position_size_pct=Decimal("10.00"),
            daily_loss_limit=Decimal("1000.00"),
        )

    @patch("apps.risk_management.risk_checker._check_market_hours")
    @patch("apps.execution_engine.executor.AlpacaClient")
    def test_buy_signal_full_pipeline(self, mock_client_cls, mock_hours):
        """A valid buy signal creates a filled trade with cost basis."""
        mock_hours.return_value = (True, "Within market hours")

        mock_client = MagicMock()
        mock_client.submit_order.return_value = {
            "order_id": "test-order-123",
            "client_order_id": "co-123",
            "symbol": "AAPL",
            "qty": 10.0,
            "side": "buy",
            "type": "market",
            "status": "filled",
            "submitted_at": "2026-01-01T10:00:00Z",
            "filled_avg_price": 150.25,
        }
        mock_client_cls.return_value = mock_client

        signal = {
            "ticker": "AAPL",
            "action": "buy",
            "quantity": "10",
            "price": "150",
            "strategy": "momentum_v1",
            "timestamp": "2026-01-01T10:00:00Z",
        }

        trades = execute_signal(signal)
        trade = trades[0]

        self.assertEqual(trade.status, "filled")
        self.assertEqual(trade.symbol, "AAPL")
        self.assertEqual(trade.side, "buy")
        self.assertEqual(trade.quantity, Decimal("10"))
        self.assertTrue(trade.risk_approved)
        self.assertEqual(trade.broker_order_id, "test-order-123")
        self.assertEqual(trade.fill_price, Decimal("150.25"))
        self.assertEqual(trade.cost_basis, Decimal("150.25"))  # Cost basis tracked
        self.assertIn("All risk checks passed", trade.risk_reason)

    @patch("apps.risk_management.risk_checker._check_market_hours")
    @patch("apps.execution_engine.executor.AlpacaClient")
    def test_sell_after_buy_calculates_pnl(self, mock_client_cls, mock_hours):
        """Selling shares after buying should calculate realized P&L."""
        mock_hours.return_value = (True, "Within market hours")

        # Setup: create a prior buy trade with cost basis
        Trade.objects.create(
            symbol="AAPL", side="buy", quantity=Decimal("10"),
            fill_price=Decimal("150.00"), cost_basis=Decimal("150.00"),
            status="filled", strategy="momentum_v1", risk_approved=True,
        )

        mock_client = MagicMock()
        mock_client.submit_order.return_value = {
            "order_id": "test-sell-456",
            "client_order_id": "co-456",
            "symbol": "AAPL",
            "qty": 10.0,
            "side": "sell",
            "type": "market",
            "status": "filled",
            "submitted_at": "2026-01-02T10:00:00Z",
            "filled_avg_price": 160.00,
        }
        mock_client.get_positions.return_value = [{"symbol": "AAPL"}]
        mock_client_cls.return_value = mock_client

        signal = {
            "ticker": "AAPL",
            "action": "sell",
            "quantity": "10",
            "price": "160",
            "strategy": "momentum_v1",
            "timestamp": "2026-01-02T10:00:00Z",
        }

        trades = execute_signal(signal)
        trade = trades[0]

        self.assertEqual(trade.status, "filled")
        self.assertTrue(trade.risk_approved)
        # P&L = (160 - 150) * 10 = $100
        self.assertEqual(trade.realized_pnl, Decimal("100.00"))
        self.assertEqual(trade.cost_basis, Decimal("150.00"))

    def test_kill_switch_rejects_trade(self):
        """Trade is rejected when kill switch is active."""
        self.config.kill_switch_active = True
        self.config.save()

        signal = {
            "ticker": "AAPL",
            "action": "buy",
            "quantity": "10",
            "price": "150",
            "strategy": "momentum_v1",
        }

        trades = execute_signal(signal)
        trade = trades[0]

        self.assertEqual(trade.status, "rejected")
        self.assertFalse(trade.risk_approved)
        self.assertIn("Kill switch", trade.risk_reason)

    @patch("apps.risk_management.risk_checker._check_market_hours")
    def test_sell_below_cost_rejected(self, mock_hours):
        """Sell at a loss is rejected by the sell-above-cost check."""
        mock_hours.return_value = (True, "Within market hours")

        # Setup: bought at $200
        Trade.objects.create(
            symbol="TSLA", side="buy", quantity=Decimal("5"),
            fill_price=Decimal("200.00"), cost_basis=Decimal("200.00"),
            status="filled", strategy="momentum_v1", risk_approved=True,
        )

        signal = {
            "ticker": "TSLA",
            "action": "sell",
            "quantity": "5",
            "price": "180",  # Below cost basis of $200
            "strategy": "momentum_v1",
        }

        trades = execute_signal(signal)
        trade = trades[0]

        self.assertEqual(trade.status, "rejected")
        self.assertFalse(trade.risk_approved)
        self.assertIn("cost basis", trade.risk_reason.lower())

    @patch("apps.risk_management.risk_checker._check_market_hours")
    def test_daily_trade_limit_blocks(self, mock_hours):
        """Trade is rejected when daily trade count is exceeded."""
        mock_hours.return_value = (True, "Within market hours")
        self.config.max_daily_trades = 2
        self.config.save()

        # Create 2 existing trades today
        for i in range(2):
            Trade.objects.create(
                symbol=f"SYM{i}", side="buy", quantity=Decimal("1"),
                status="pending", strategy="test",
            )

        signal = {
            "ticker": "AAPL",
            "action": "buy",
            "quantity": "10",
            "price": "150",
            "strategy": "momentum_v1",
        }

        trades = execute_signal(signal)
        trade = trades[0]

        # The trade itself is the 3rd, but 2 existed before + this one = 3 > limit of 2
        # Actually the check runs AFTER creating the trade record, so count = 3 >= 2
        self.assertEqual(trade.status, "rejected")
        self.assertFalse(trade.risk_approved)
        self.assertIn("trade limit", trade.risk_reason.lower())
