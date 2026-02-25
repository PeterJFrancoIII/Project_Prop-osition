"""
Risk configuration models.

Stores per-account risk parameters. All trading parameters
live in the database (not hardcoded) per scalability rules.
"""

from django.db import models


class RiskConfig(models.Model):
    """
    Risk parameters for a trading account.

    Configuration-driven: these values are read by the risk checker
    before every trade. Change them in the database or admin,
    not in code.
    """

    name = models.CharField(max_length=100, unique=True, default="default")
    is_active = models.BooleanField(default=True)

    # Drawdown limits
    max_daily_drawdown_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        help_text="Maximum daily loss as % of account equity"
    )
    max_total_drawdown_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        help_text="Maximum total drawdown as % of starting equity"
    )

    # Position limits
    max_position_size_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        help_text="Maximum position size as % of account equity"
    )
    max_open_positions = models.IntegerField(
        default=10, help_text="Maximum number of concurrent open positions"
    )

    # Daily limits
    max_daily_trades = models.IntegerField(
        default=50, help_text="Maximum trades per day (PDT awareness)"
    )
    daily_loss_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=1000.00,
        help_text="Maximum dollar loss per day before auto-stop"
    )

    # Kill switch
    kill_switch_active = models.BooleanField(
        default=False,
        help_text="When True, ALL trading is halted immediately"
    )

    # Multi-tenant
    organization_id = models.IntegerField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Risk Configuration"
        verbose_name_plural = "Risk Configurations"

    def __str__(self):
        status = "🔴 KILL SWITCH" if self.kill_switch_active else "🟢 Active"
        return f"{self.name} | {status} | Max DD: {self.max_daily_drawdown_pct}%"
