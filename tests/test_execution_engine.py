"""
Execution engine tests.

Tests the execute_signal pipeline with mocked broker.
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase

from apps.execution_engine.models import Trade
from apps.execution_engine.executor import execute_signal


class ExecuteSignalTest(TestCase):
    """Tests for the execute_signal pipeline."""

    def setUp(self):
        self.signal = {
            "ticker": "AAPL",
            "action": "buy",
            "quantity": "10",
            "price": "185.50",
            "strategy": "stock_momentum_v1",
            "timestamp": "2026-02-25T12:00:00Z",
        }

    @patch("apps.execution_engine.executor.AlpacaClient")
    @patch("apps.execution_engine.executor.check_trade")
    def test_successful_execution_creates_trade(self, mock_risk, mock_alpaca_cls):
        """Valid signal → approved → order submitted → Trade created."""
        mock_risk.return_value = (True, "Approved")

        mock_client = MagicMock()
        mock_client.submit_order.return_value = {
            "order_id": "broker-order-123",
            "client_order_id": "client-123",
            "symbol": "AAPL",
            "qty": 10.0,
            "side": "buy",
            "type": "market",
            "status": "accepted",
            "submitted_at": "2026-02-25T12:00:00Z",
            "filled_avg_price": None,
        }
        mock_alpaca_cls.return_value = mock_client

        trade = execute_signal(self.signal)

        self.assertEqual(trade.symbol, "AAPL")
        self.assertEqual(trade.side, "buy")
        self.assertEqual(trade.quantity, Decimal("10"))
        self.assertEqual(trade.status, "submitted")
        self.assertTrue(trade.risk_approved)
        self.assertEqual(trade.broker_order_id, "broker-order-123")
        self.assertEqual(Trade.objects.count(), 1)

    @patch("apps.execution_engine.executor.check_trade")
    def test_risk_rejection_blocks_trade(self, mock_risk):
        """Risk check rejection → trade rejected, no broker call."""
        mock_risk.return_value = (False, "Daily loss limit exceeded")

        trade = execute_signal(self.signal)

        self.assertEqual(trade.status, "rejected")
        self.assertFalse(trade.risk_approved)
        self.assertIn("Daily loss limit", trade.risk_reason)
        self.assertEqual(trade.broker_order_id, "")

    @patch("apps.execution_engine.executor.AlpacaClient")
    @patch("apps.execution_engine.executor.check_trade")
    def test_broker_error_logged(self, mock_risk, mock_alpaca_cls):
        """Broker failure → trade status=error, exception raised."""
        mock_risk.return_value = (True, "Approved")

        mock_client = MagicMock()
        mock_client.submit_order.side_effect = Exception("Connection timeout")
        mock_alpaca_cls.return_value = mock_client

        with self.assertRaises(Exception):
            execute_signal(self.signal)

        trade = Trade.objects.first()
        self.assertEqual(trade.status, "error")
        self.assertIn("Connection timeout", trade.error_message)
