"""
Root URL configuration for Proprietary Accounts Auto-Trader.

All API endpoints live under /api/v1/ (versioned from day one).
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Dashboard (Root)
    path("", include("apps.dashboard.urls")),
    # API v1 — all app endpoints nested here
    path("api/v1/webhooks/", include("apps.webhooks.urls")),
    path("api/v1/trades/", include("apps.execution_engine.urls")),
    path("api/v1/broker/", include("apps.broker_connector.urls")),
    path("api/v1/risk/", include("apps.risk_management.urls")),
]
