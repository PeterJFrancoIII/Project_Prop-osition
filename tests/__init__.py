"""
Webhook receiver tests.

Tests the TradingView webhook endpoint for valid/invalid payloads,
authentication, and signal dispatch.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.webhooks.models import WebhookEvent


@override_settings(WEBHOOK_AUTH_TOKEN="test-token-123")
class WebhookReceiveViewTest(TestCase):
    """Tests for POST /api/v1/webhooks/tradingview/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/webhooks/tradingview/"
        self.valid_payload = {
            "ticker": "AAPL",
            "action": "buy",
            "quantity": "10",
            "price": "185.50",
            "strategy": "stock_momentum_v1",
            "timestamp": "2026-02-25T12:00:00Z",
        }
        self.headers = {"HTTP_X_API_TOKEN": "test-token-123"}

    def test_valid_webhook_creates_event(self):
        """Valid webhook with correct token creates a WebhookEvent."""
        with patch("apps.webhooks.views.execute_signal") as mock_execute:
            mock_trade = MagicMock()
            mock_trade.trade_id = "trd_test123"
            mock_trade.symbol = "AAPL"
            mock_trade.side = "buy"
            mock_trade.quantity = "10"
            mock_execute.return_value = mock_trade

            response = self.client.post(
                self.url,
                self.valid_payload,
                format="json",
                **self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(WebhookEvent.objects.count(), 1)

        event = WebhookEvent.objects.first()
        self.assertEqual(event.ticker, "AAPL")
        self.assertEqual(event.action, "buy")
        self.assertEqual(event.status, "dispatched")

    def test_invalid_token_returns_401(self):
        """Wrong auth token returns 401 and creates no dispatched event."""
        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
            HTTP_X_API_TOKEN="wrong-token",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(WebhookEvent.objects.count(), 0)

    def test_missing_token_returns_401(self):
        """No auth token returns 401."""
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, 401)

    def test_missing_required_field_returns_400(self):
        """Missing 'action' field returns 400 with validation error."""
        payload = {
            "ticker": "AAPL",
            "quantity": "10",
            "strategy": "test_v1",
        }
        response = self.client.post(
            self.url, payload, format="json", **self.headers
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")

        # Event should be logged as rejected
        event = WebhookEvent.objects.first()
        self.assertIsNotNone(event)
        self.assertEqual(event.status, "rejected")

    def test_invalid_action_returns_400(self):
        """Invalid action value returns 400."""
        payload = self.valid_payload.copy()
        payload["action"] = "hold"  # Not a valid choice
        response = self.client.post(
            self.url, payload, format="json", **self.headers
        )
        self.assertEqual(response.status_code, 400)

    def test_negative_quantity_returns_400(self):
        """Negative quantity returns 400."""
        payload = self.valid_payload.copy()
        payload["quantity"] = "-5"
        response = self.client.post(
            self.url, payload, format="json", **self.headers
        )
        self.assertEqual(response.status_code, 400)

    def test_execution_error_returns_500(self):
        """If execution engine throws, returns 500 and logs error."""
        with patch("apps.webhooks.views.execute_signal") as mock_execute:
            mock_execute.side_effect = Exception("Broker connection failed")

            response = self.client.post(
                self.url,
                self.valid_payload,
                format="json",
                **self.headers,
            )

        self.assertEqual(response.status_code, 500)
        event = WebhookEvent.objects.first()
        self.assertEqual(event.status, "error")
        self.assertIn("Broker connection failed", event.error_message)
