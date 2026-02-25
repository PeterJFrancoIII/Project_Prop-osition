"""
Trade models.

Full audit trail for every order submitted through the system.
Trade records are append-only — core fields are never modified after creation.
"""

import time
from django.db import models


def generate_trade_id():
    """Generate a prefixed unique ID for trades."""
    return f"trd_{int(time.time() * 1000)}"


class Trade(models.Model):
    """
    Immutable record of a trade executed by the system.

    Core fields (symbol, side, quantity, fill_price, created_at) are
    NEVER modified after creation per data governance rules.
    Corrections create new adjustment records.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("submitted", "Submitted"),
        ("filled", "Filled"),
        ("partial", "Partially Filled"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected"),
        ("error", "Error"),
    ]

    SIDE_CHOICES = [
        ("buy", "Buy"),
        ("sell", "Sell"),
    ]

    trade_id = models.CharField(
        max_length=64, unique=True, default=generate_trade_id, editable=False
    )
    symbol = models.CharField(max_length=20, db_index=True)
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    quantity = models.DecimalField(max_digits=15, decimal_places=6)
    order_type = models.CharField(max_length=20, default="market")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Pricing
    requested_price = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    fill_price = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    cost_basis = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)

    # P&L tracking
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default="0.00")
    commission = models.DecimalField(max_digits=10, decimal_places=4, default="0.0000")

    # Source tracking
    strategy = models.CharField(max_length=100, db_index=True)
    webhook_id = models.CharField(max_length=64, blank=True, default="")
    broker_order_id = models.CharField(max_length=128, blank=True, default="")

    # Broker info
    broker_type = models.CharField(max_length=30, default="alpaca")
    broker_account_id = models.CharField(max_length=64, blank=True, default="")

    # Error tracking
    error_message = models.TextField(blank=True, default="")

    # Risk check result
    risk_approved = models.BooleanField(default=False)
    risk_reason = models.CharField(max_length=200, blank=True, default="")

    # Multi-tenant support (Layer 4+)
    user_id = models.IntegerField(null=True, blank=True)
    organization_id = models.IntegerField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Trade"
        verbose_name_plural = "Trades"

    def __str__(self):
        return f"{self.trade_id} | {self.side} {self.quantity} {self.symbol} @ {self.fill_price or 'pending'} | {self.status}"
