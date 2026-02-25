from django.contrib import admin
from .models import RiskConfig
from .prop_firm_models import PropFirmAccount


@admin.register(RiskConfig)
class RiskConfigAdmin(admin.ModelAdmin):
    list_display = [
        "name", "is_active", "kill_switch_active",
        "max_daily_drawdown_pct", "max_position_size_pct",
        "max_open_positions", "daily_loss_limit", "updated_at",
    ]
    list_filter = ["is_active", "kill_switch_active"]
    list_editable = ["kill_switch_active"]  # Quick toggle from list view


@admin.register(PropFirmAccount)
class PropFirmAccountAdmin(admin.ModelAdmin):
    list_display = [
        "name", "firm", "phase", "is_active",
        "account_size", "current_equity", "total_pnl",
        "progress_pct", "trading_days_completed", "updated_at",
    ]
    list_filter = ["firm", "phase", "is_active"]
    list_editable = ["is_active", "phase"]

