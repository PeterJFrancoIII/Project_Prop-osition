from django.contrib import admin
from .models import Strategy, AIModel


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = [
        "strategy_id", "name", "is_active", "asset_class",
        "timeframe", "ai_model", "position_size_pct", "updated_at",
    ]
    list_filter = ["is_active", "asset_class", "timeframe", "ai_model"]
    list_editable = ["is_active"]
    search_fields = ["name", "strategy_id"]


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = [
        "name", "model_type", "version", "status",
        "accuracy", "sharpe_ratio", "last_trained",
    ]
    list_filter = ["model_type", "status"]
