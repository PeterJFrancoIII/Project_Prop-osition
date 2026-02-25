"""
Prop firm account models.

Tracks challenge progress, P&L vs. firm limits,
and prop firm-specific rule compliance.
"""

from decimal import Decimal
from django.db import models


class PropFirmAccount(models.Model):
    """
    Represents a prop firm trading account or challenge.

    Tracks challenge phase, P&L progress, and firm-specific risk limits.
    The risk checker reads these limits to auto-stop before violation.
    """

    PHASE_CHOICES = [
        ("evaluation", "Evaluation"),
        ("verification", "Verification"),
        ("funded", "Funded"),
        ("suspended", "Suspended"),
        ("failed", "Failed"),
    ]

    FIRM_CHOICES = [
        ("trade_the_pool", "Trade The Pool"),
        ("ftmo", "FTMO"),
        ("topstep", "Topstep"),
        ("apex_trader", "Apex Trader Funding"),
        ("dna_funded", "DNA Funded"),
        ("hyro_trader", "HyroTrader"),
        ("crypto_fund_trader", "Crypto Fund Trader"),
        ("other", "Other"),
    ]

    # Identity
    name = models.CharField(max_length=100, help_text="Display name, e.g. 'FTMO 100K Challenge #2'")
    firm = models.CharField(max_length=30, choices=FIRM_CHOICES)
    account_number = models.CharField(max_length=64, blank=True, default="")

    # Phase & Status
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default="evaluation")
    is_active = models.BooleanField(default=True)

    # Account Size
    account_size = models.DecimalField(
        max_digits=15, decimal_places=2, default=50000,
        help_text="Starting account size ($)"
    )
    # Firm-Specific Limits
    max_daily_drawdown_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        help_text="Firm's max daily drawdown % (e.g., 5%)"
    )
    max_total_drawdown_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        help_text="Firm's max total drawdown % (e.g., 10%)"
    )
    profit_target_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        help_text="Profit target % to pass the phase (e.g., 10%)"
    )
    profit_split_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=80.00,
        help_text="Your profit split % on funded account (e.g., 80%)"
    )
    min_trading_days = models.IntegerField(
        default=10, help_text="Minimum trading days required"
    )

    # Tracking
    trading_days_completed = models.IntegerField(default=0)
    challenge_start_date = models.DateField(null=True, blank=True)
    challenge_end_date = models.DateField(null=True, blank=True)

    # Link to broker
    broker_account_id = models.CharField(max_length=64, blank=True, default="")

    # Multi-tenant
    organization_id = models.IntegerField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Prop Firm Account"
        verbose_name_plural = "Prop Firm Accounts"

    def __str__(self):
        return f"{self.name} | {self.get_firm_display()} | {self.get_phase_display()} | ${self.current_equity}"

    # ── Calculated Properties ──

    @property
    def profit_target_amount(self) -> Decimal:
        """Dollar amount needed to hit the profit target."""
        return self.account_size * (self.profit_target_pct / Decimal("100"))

    @property
    def total_pnl(self) -> Decimal:
        """Dynamic total realized P&L across all executed trades for this account."""
        from apps.execution_engine.models import Trade
        if not self.broker_account_id:
            return Decimal("0.00")
            
        trades = Trade.objects.filter(broker_account_id=self.broker_account_id, status="filled")
        total = Decimal("0.00")
        for t in trades:
            if t.realized_pnl is not None:
                total += Decimal(str(t.realized_pnl))
        return total

    @property
    def current_equity(self) -> Decimal:
        """Current dynamic equity calculated from base account size + Trade realized P&L."""
        return Decimal(str(self.account_size)) + self.total_pnl

    @property
    def progress_pct(self) -> Decimal:
        """Progress toward profit target as a percentage (0-100+)."""
        target = self.profit_target_amount
        if target <= Decimal("0"):
            return Decimal("0")
        return (self.total_pnl / target) * Decimal("100")

    @property
    def max_daily_drawdown_amount(self) -> Decimal:
        """Max daily loss allowed in dollars."""
        return self.account_size * (self.max_daily_drawdown_pct / Decimal("100"))

    @property
    def max_total_drawdown_amount(self) -> Decimal:
        """Max total drawdown allowed in dollars."""
        return self.account_size * (self.max_total_drawdown_pct / Decimal("100"))

    @property
    def total_drawdown_pct(self) -> Decimal:
        """Current total drawdown as percentage of account size."""
        if self.total_pnl >= 0:
            return Decimal("0")
        return abs(self.total_pnl) / self.account_size * Decimal("100")

    @property
    def is_passing(self) -> bool:
        """Whether the account is currently in a passing state."""
        # Not failed AND total drawdown within limits
        if self.phase == "failed":
            return False
        if self.total_drawdown_pct >= self.max_total_drawdown_pct:
            return False
        return True

    @property
    def pnl_remaining(self) -> Decimal:
        """Dollar amount still needed to hit profit target."""
        return self.profit_target_amount - self.total_pnl

    def check_compliance(self) -> tuple[bool, str]:
        """
        Check if the account is in compliance with firm rules.

        Returns (compliant, reason).
        """
        if self.phase == "failed":
            return (False, "Account has failed the challenge")

        if self.total_drawdown_pct >= self.max_total_drawdown_pct:
            return (False, f"Total drawdown {self.total_drawdown_pct:.2f}% exceeds limit {self.max_total_drawdown_pct}%")

        return (True, "Account in compliance")
