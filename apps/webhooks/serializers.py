"""
Webhook payload serializers.

Validates incoming TradingView webhook JSON payloads.
"""

from rest_framework import serializers


class TradingViewWebhookSerializer(serializers.Serializer):
    """
    Validates the JSON payload from a TradingView webhook alert.

    Expected payload:
    {
        "ticker": "AAPL",
        "action": "buy",
        "quantity": "1",
        "price": "185.50",
        "strategy": "stock_momentum_v1",
        "timestamp": "2026-02-25T12:00:00Z"
    }
    """

    ticker = serializers.CharField(max_length=20)
    action = serializers.ChoiceField(choices=["buy", "sell"])
    quantity = serializers.CharField(max_length=20)
    price = serializers.CharField(
        max_length=20, required=False, default="0"
    )
    strategy = serializers.CharField(max_length=100)
    timestamp = serializers.CharField(required=False, default="")

    def validate_quantity(self, value):
        """Ensure quantity is a positive number."""
        try:
            qty = float(value)
            if qty <= 0:
                raise serializers.ValidationError("Quantity must be positive.")
        except ValueError:
            raise serializers.ValidationError("Quantity must be a valid number.")
        return value
