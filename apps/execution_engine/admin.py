from django.contrib import admin
from .models import Trade


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = [
        "trade_id", "symbol", "side", "quantity", "fill_price",
        "status", "strategy", "risk_approved", "created_at",
    ]
    list_filter = ["status", "side", "strategy", "broker_type", "risk_approved"]
    search_fields = ["trade_id", "symbol", "strategy", "broker_order_id"]
    readonly_fields = [
        "trade_id", "symbol", "side", "quantity", "order_type",
        "requested_price", "fill_price", "cost_basis",
        "realized_pnl", "commission",
        "strategy", "webhook_id", "broker_order_id",
        "broker_type", "broker_account_id",
        "risk_approved", "risk_reason", "error_message",
        "created_at", "updated_at",
    ]
    ordering = ["-created_at"]
