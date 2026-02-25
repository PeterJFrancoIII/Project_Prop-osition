from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Overview
    path("", views.overview, name="overview"),
    path("stats/", views.overview_stats_partial, name="overview-stats"),
    path("recent-trades/", views.recent_trades_partial, name="recent-trades"),
    path("recent-activity/", views.recent_activity_partial, name="recent-activity"),

    # Trade History
    path("trades/", views.trades, name="trades"),

    # Activity Log
    path("activity/", views.activity, name="activity"),

    # Strategies & AI Models
    path("strategies/", views.strategies, name="strategies"),
    path("strategies/<int:strategy_id>/toggle/", views.toggle_strategy, name="toggle-strategy"),
    path("strategies/<int:strategy_id>/update/", views.update_strategy, name="update-strategy"),

    # Risk Management
    path("risk/", views.risk, name="risk"),
    path("risk/update/", views.update_risk, name="update-risk"),
    path("risk/kill-switch/", views.kill_switch, name="kill-switch"),

    # System Health
    path("system/", views.system, name="system"),

    # Accounts
    path("accounts/", views.accounts, name="accounts"),

    # API (JSON)
    path("api/equity-data/", views.equity_data_api, name="equity-data"),
]
