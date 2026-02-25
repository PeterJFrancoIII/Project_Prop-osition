from django.contrib import admin
from .models import WebhookEvent


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ["webhook_id", "source", "ticker", "action", "status", "created_at"]
    list_filter = ["status", "source", "action"]
    search_fields = ["webhook_id", "ticker", "strategy"]
    readonly_fields = [
        "webhook_id", "source", "payload", "status", "error_message",
        "ticker", "action", "quantity", "strategy", "created_at", "ip_address",
    ]
    ordering = ["-created_at"]
