"""
Broker account models.

Stores broker configurations and encrypted API credentials.
"""

import time
from django.db import models


def generate_account_id():
    """Generate a prefixed unique ID for broker accounts."""
    return f"acct_{int(time.time() * 1000)}"


class BrokerAccount(models.Model):
    """
    Represents a connection to an external broker or exchange.

    API keys are stored encrypted via Fernet. The decrypted keys
    are never exposed in API responses or logs.
    """

    BROKER_CHOICES = [
        ("alpaca", "Alpaca"),
        ("interactive_brokers", "Interactive Brokers"),
        ("ccxt", "CCXT (Crypto)"),
    ]

    MODE_CHOICES = [
        ("paper", "Paper Trading"),
        ("live", "Live Trading"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("error", "Error"),
    ]

    account_id = models.CharField(
        max_length=64, unique=True, default=generate_account_id, editable=False
    )
    broker_type = models.CharField(max_length=30, choices=BROKER_CHOICES, default="alpaca")
    display_name = models.CharField(max_length=100, help_text="Friendly name for this account")
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="paper")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")

    # Encrypted credentials (stored as Fernet-encrypted strings)
    encrypted_api_key = models.TextField(blank=True, default="")
    encrypted_secret_key = models.TextField(blank=True, default="")
    base_url = models.URLField(blank=True, default="https://paper-api.alpaca.markets")

    # Account info (updated on sync)
    buying_power = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    equity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cash = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    # Multi-tenant support (Layer 4+)
    user_id = models.IntegerField(null=True, blank=True)
    organization_id = models.IntegerField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Broker Account"
        verbose_name_plural = "Broker Accounts"

    def __str__(self):
        return f"{self.account_id} | {self.broker_type} ({self.mode}) | {self.display_name}"

    @property
    def api_key_masked(self):
        """Return masked API key for display (never expose full key)."""
        if self.encrypted_api_key:
            return "****" + self.encrypted_api_key[-4:] if len(self.encrypted_api_key) > 4 else "****"
        return ""
