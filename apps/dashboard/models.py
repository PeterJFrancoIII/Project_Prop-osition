"""
Strategy models.

Defines configurable trading strategies and AI models.
All strategy parameters live in the database (not code) per scalability rules.
"""

import time
from django.db import models


def generate_strategy_id():
    """Generate a prefixed unique ID for strategies."""
    return f"stg_{int(time.time() * 1000)}"


class Strategy(models.Model):
    """
    A trading strategy that can be toggled, configured, and monitored.

    Parameters are editable from the dashboard — no code deploy needed.
    """

    ASSET_CLASS_CHOICES = [
        ("stocks", "Stocks"),
        ("futures", "Futures"),
        ("crypto", "Crypto"),
    ]

    TIMEFRAME_CHOICES = [
        ("1m", "1 Minute"),
        ("5m", "5 Minutes"),
        ("15m", "15 Minutes"),
        ("1h", "1 Hour"),
        ("4h", "4 Hours"),
        ("1d", "Daily"),
        ("1w", "Weekly"),
    ]

    AI_MODEL_CHOICES = [
        ("none", "None (Rules Only)"),
        ("sentiment", "Sentiment NLP"),
        ("regime", "Regime Detection (HMM)"),
        ("reinforcement", "Reinforcement Learning"),
        ("ensemble", "Ensemble (All Models)"),
    ]

    strategy_id = models.CharField(
        max_length=64, unique=True, default=generate_strategy_id, editable=False
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=False)

    # Configuration
    asset_class = models.CharField(max_length=20, choices=ASSET_CLASS_CHOICES, default="stocks")
    timeframe = models.CharField(max_length=5, choices=TIMEFRAME_CHOICES, default="1d")
    symbols = models.JSONField(
        default=list, blank=True,
        help_text="List of ticker symbols this strategy trades"
    )

    account_numbers = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Comma-separated broker_account_id strings where this strategy runs"
    )

    # Position management
    position_size_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.00,
        help_text="Position size as % of account equity"
    )
    max_positions = models.IntegerField(default=5)
    stop_loss_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.00,
        help_text="Stop loss as % from entry"
    )
    take_profit_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=4.00,
        help_text="Take profit as % from entry"
    )

    # AI model configuration
    ai_model = models.CharField(max_length=30, choices=AI_MODEL_CHOICES, default="none")
    ai_confidence_threshold = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.70,
        help_text="Min confidence score to act on AI signal (0-1)"
    )
    ai_retrain_freq = models.CharField(max_length=20, default="weekly")

    # Custom parameters (JSON blob for strategy-specific config)
    custom_params = models.JSONField(
        default=dict, blank=True,
        help_text="Strategy-specific parameters as JSON"
    )

    # Multi-tenant
    organization_id = models.IntegerField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Strategy"
        verbose_name_plural = "Strategies"

    def __str__(self):
        status = "🟢" if self.is_active else "⏸️"
        return f"{status} {self.name} | {self.asset_class} | {self.timeframe} | AI: {self.ai_model}"


class AIModel(models.Model):
    """
    Registry of AI models available for strategies.

    Stub for Layer 0 — actual model training/inference in Layer 3.
    """

    MODEL_TYPE_CHOICES = [
        ("sentiment", "Sentiment NLP"),
        ("regime", "Regime Detection"),
        ("reinforcement", "Reinforcement Learning"),
        ("prediction", "Price Prediction"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("training", "Training"),
        ("retired", "Retired"),
    ]

    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=30, choices=MODEL_TYPE_CHOICES)
    version = models.CharField(max_length=20, default="0.1.0")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    description = models.TextField(blank=True, default="")
    last_trained = models.DateTimeField(null=True, blank=True)

    # Performance metrics
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sharpe_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "AI Model"
        verbose_name_plural = "AI Models"

    def __str__(self):
        return f"{self.name} v{self.version} ({self.model_type}) [{self.status}]"

    @property
    def strategies_count(self):
        """Number of strategies using this model type."""
        return Strategy.objects.filter(ai_model=self.model_type).count()
