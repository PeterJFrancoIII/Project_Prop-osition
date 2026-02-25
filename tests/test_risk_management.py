"""
Risk management tests.

Layer 0: Tests the passthrough stub.
Layer 1: Will add tests for actual risk checks.
"""

from django.test import TestCase
from apps.risk_management.risk_checker import check_trade


class RiskCheckerTest(TestCase):
    """Tests for the risk checker."""

    def test_passthrough_approves_valid_signal(self):
        """Layer 0 passthrough always returns (True, ...)."""
        signal = {
            "ticker": "AAPL",
            "action": "buy",
            "quantity": "10",
            "strategy": "test_v1",
        }
        approved, reason = check_trade(signal, account=None)
        self.assertTrue(approved)
        self.assertIn("Layer 0", reason)

    def test_passthrough_approves_sell(self):
        """Sell signals also pass through in Layer 0."""
        signal = {
            "ticker": "TSLA",
            "action": "sell",
            "quantity": "5",
            "strategy": "test_v1",
        }
        approved, reason = check_trade(signal, account=None)
        self.assertTrue(approved)
