"""
Webhook event models.

Logs every incoming webhook for audit trail and debugging.
"""

import time
from django.db import models


def generate_webhook_id():
    """Generate a prefixed unique ID for webhook events."""
    return f"wh_{int(time.time() * 1000)}"


class WebhookEvent(models.Model):
    """
    Immutable log of every incoming webhook request.

    Every webhook — valid or invalid — is recorded here for audit.
    """

    STATUS_CHOICES = [
        ("received", "Received"),
        ("validated", "Validated"),
        ("dispatched", "Dispatched"),
        ("rejected", "Rejected"),
        ("error", "Error"),
    ]

    webhook_id = models.CharField(
        max_length=64, unique=True, default=generate_webhook_id, editable=False
    )
    source = models.CharField(max_length=50, default="tradingview")
    payload = models.JSONField(help_text="Raw JSON payload from the webhook")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="received")
    error_message = models.TextField(blank=True, default="")

    # Parsed signal fields (populated on successful validation)
    ticker = models.CharField(max_length=20, blank=True, default="")
    action = models.CharField(max_length=10, blank=True, default="")
    quantity = models.CharField(max_length=20, blank=True, default="")
    strategy = models.CharField(max_length=100, blank=True, default="")

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Webhook Event"
        verbose_name_plural = "Webhook Events"

    def __str__(self):
        return f"{self.webhook_id} | {self.source} | {self.status} | {self.ticker}"
