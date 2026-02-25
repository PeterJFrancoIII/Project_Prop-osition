"""
Trade history API views.
"""

from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Trade


class TradeSerializer(serializers.ModelSerializer):
    """Serializer for trade records (read-only — trades are immutable)."""

    class Meta:
        model = Trade
        fields = [
            "trade_id", "symbol", "side", "quantity", "order_type", "status",
            "requested_price", "fill_price", "cost_basis",
            "realized_pnl", "commission",
            "strategy", "webhook_id", "broker_order_id",
            "broker_type", "broker_account_id",
            "risk_approved", "risk_reason",
            "error_message", "created_at", "updated_at",
        ]
        read_only_fields = fields  # Trades are append-only


class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/trades/ — List all trades (paginated).
    GET /api/v1/trades/{trade_id}/ — Retrieve a single trade.

    Read-only: trades are created by the execution engine, not via API.
    """

    queryset = Trade.objects.all()
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "trade_id"
    filterset_fields = ["symbol", "side", "status", "strategy"]
