from django.contrib import admin
from .models import RiskConfig


@admin.register(RiskConfig)
class RiskConfigAdmin(admin.ModelAdmin):
    list_display = [
        "name", "is_active", "kill_switch_active",
        "max_daily_drawdown_pct", "max_position_size_pct",
        "max_open_positions", "daily_loss_limit", "updated_at",
    ]
    list_filter = ["is_active", "kill_switch_active"]
    list_editable = ["kill_switch_active"]  # Quick toggle from list view
