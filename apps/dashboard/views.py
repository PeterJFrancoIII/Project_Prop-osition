"""
Dashboard views — powers all dashboard pages.

Each view provides context data from the models to its corresponding template.
HTMX partial endpoints return HTML fragments for live updates.
"""

import sys
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from itertools import accumulate

import django
from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.broker_connector.models import BrokerAccount
from apps.execution_engine.models import Trade
from apps.risk_management.models import RiskConfig
from apps.risk_management.prop_firm_models import PropFirmAccount
from apps.webhooks.models import WebhookEvent
from .models import AIModel, Strategy

logger = logging.getLogger(__name__)


def _get_risk_config():
    """Get or create the default risk configuration."""
    config, _ = RiskConfig.objects.get_or_create(name="default")
    return config


def _get_kill_switch_status():
    """Check if kill switch is active (used by base template context)."""
    config = _get_risk_config()
    return config.kill_switch_active


def _base_context():
    """Context shared by all dashboard pages (injected into base template)."""
    return {
        "kill_switch_active": _get_kill_switch_status(),
    }


# ──────────────────────────────────────────────
# Overview Page
# ──────────────────────────────────────────────

def overview(request):
    """Dashboard overview — key metrics, recent trades, activity feed, strategies."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Today's trades
    trades_today_qs = Trade.objects.filter(created_at__gte=today_start)
    trades_today = trades_today_qs.count()
    trades_won = trades_today_qs.filter(realized_pnl__gt=0).count()
    trades_lost = trades_today_qs.filter(realized_pnl__lt=0).count()

    # P&L
    total_pnl = sum(t.realized_pnl for t in trades_today_qs if t.realized_pnl) or Decimal("0.00")

    # Win rate
    filled_trades = Trade.objects.filter(status="filled")
    total_filled = filled_trades.count()
    wins = filled_trades.filter(realized_pnl__gt=0).count()
    win_rate = (wins / total_filled * 100) if total_filled > 0 else 0

    # Risk config
    risk_config = _get_risk_config()

    # Strategies
    strategies = Strategy.objects.all()
    active_strategies = strategies.filter(is_active=True).count()

    # Equity — try live Alpaca, fallback to placeholder
    account_equity = Decimal("100000.00")
    try:
        from apps.broker_connector.alpaca_client import AlpacaClient
        client = AlpacaClient()
        acct = client.get_account()
        account_equity = Decimal(str(acct["equity"]))
    except Exception:
        pass  # Use placeholder sync from Alpaca

    ctx = {
        **_base_context(),
        "active_page": "overview",
        "system_status": "online",
        # Stats
        "total_pnl": total_pnl,
        "trades_today": trades_today,
        "trades_won": trades_won,
        "trades_lost": trades_lost,
        "account_equity": account_equity,
        "active_strategies": active_strategies,
        "total_strategies": strategies.count(),
        "win_rate": win_rate,
        "daily_drawdown": Decimal("0.00"),  # Placeholder
        "max_daily_drawdown": risk_config.max_daily_drawdown_pct,
        # Tables
        "recent_trades": Trade.objects.all()[:10],
        "recent_events": WebhookEvent.objects.all()[:10],
        "strategies": strategies,
    }
    return render(request, "dashboard/overview.html", ctx)


def overview_stats_partial(request):
    """HTMX partial: refreshes the stats grid on the overview page."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    trades_today_qs = Trade.objects.filter(created_at__gte=today_start)
    trades_today = trades_today_qs.count()
    trades_won = trades_today_qs.filter(realized_pnl__gt=0).count()
    trades_lost = trades_today_qs.filter(realized_pnl__lt=0).count()
    total_pnl = sum(t.realized_pnl for t in trades_today_qs if t.realized_pnl) or Decimal("0.00")

    filled_trades = Trade.objects.filter(status="filled")
    total_filled = filled_trades.count()
    wins = filled_trades.filter(realized_pnl__gt=0).count()
    win_rate = (wins / total_filled * 100) if total_filled > 0 else 0

    risk_config = _get_risk_config()
    strategies = Strategy.objects.all()

    ctx = {
        "total_pnl": total_pnl,
        "trades_today": trades_today,
        "trades_won": trades_won,
        "trades_lost": trades_lost,
        "account_equity": Decimal("100000.00"),
        "active_strategies": strategies.filter(is_active=True).count(),
        "total_strategies": strategies.count(),
        "win_rate": win_rate,
        "daily_drawdown": Decimal("0.00"),
        "max_daily_drawdown": risk_config.max_daily_drawdown_pct,
    }
    return render(request, "dashboard/_partials/stats_grid.html", ctx)


def recent_trades_partial(request):
    """HTMX partial: recent trades table body."""
    trades = Trade.objects.all()[:10]
    return render(request, "dashboard/_partials/recent_trades.html", {
        "recent_trades": trades,
    })


def recent_activity_partial(request):
    """HTMX partial: recent activity feed."""
    events = WebhookEvent.objects.all()[:10]
    return render(request, "dashboard/_partials/recent_activity.html", {
        "recent_events": events,
    })


# ──────────────────────────────────────────────
# Trade History Page
# ──────────────────────────────────────────────

def trades(request):
    """Full trade history with filters and pagination."""
    qs = Trade.objects.all()

    # Apply filters
    filters = {}
    symbol = request.GET.get("symbol", "").strip()
    side = request.GET.get("side", "").strip()
    status = request.GET.get("status", "").strip()
    strategy = request.GET.get("strategy", "").strip()

    if symbol:
        qs = qs.filter(symbol__icontains=symbol)
        filters["symbol"] = symbol
    if side:
        qs = qs.filter(side=side)
        filters["side"] = side
    if status:
        qs = qs.filter(status=status)
        filters["status"] = status
    if strategy:
        qs = qs.filter(strategy__icontains=strategy)
        filters["strategy"] = strategy

    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    ctx = {
        **_base_context(),
        "active_page": "trades",
        "trades": page_obj,
        "filters": filters,
    }
    return render(request, "dashboard/trades.html", ctx)


# ──────────────────────────────────────────────
# Activity Log Page
# ──────────────────────────────────────────────

def activity(request):
    """Full webhook event log with pagination."""
    qs = WebhookEvent.objects.all()
    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    ctx = {
        **_base_context(),
        "active_page": "activity",
        "events": page_obj,
    }
    return render(request, "dashboard/activity.html", ctx)


# ──────────────────────────────────────────────
# Strategies & AI Models Page
# ──────────────────────────────────────────────

def strategies(request):
    """Strategy management with AI model configuration."""
    ctx = {
        **_base_context(),
        "active_page": "strategies",
        "strategies": Strategy.objects.all(),
        "ai_models": AIModel.objects.all(),
    }
    return render(request, "dashboard/strategies.html", ctx)


@require_POST
def toggle_strategy(request, strategy_id):
    """HTMX: Toggle a strategy's active/inactive state."""
    strategy = get_object_or_404(Strategy, id=strategy_id)
    strategy.is_active = not strategy.is_active
    strategy.save()
    logger.info("Strategy %s toggled to %s", strategy.name, "ACTIVE" if strategy.is_active else "PAUSED")
    return redirect("dashboard:strategies")


@require_POST
def update_strategy(request, strategy_id):
    """HTMX: Update strategy parameters from the edit form."""
    strategy = get_object_or_404(Strategy, id=strategy_id)

    # Update fields from POST data
    if "position_size_pct" in request.POST:
        strategy.position_size_pct = Decimal(request.POST["position_size_pct"])
    if "max_positions" in request.POST:
        strategy.max_positions = int(request.POST["max_positions"])
    if "stop_loss_pct" in request.POST:
        strategy.stop_loss_pct = Decimal(request.POST["stop_loss_pct"])
    if "ai_model_type" in request.POST:
        strategy.ai_model = request.POST["ai_model_type"]
    if "ai_confidence_threshold" in request.POST:
        strategy.ai_confidence_threshold = Decimal(request.POST["ai_confidence_threshold"])
    if "ai_retrain_freq" in request.POST:
        strategy.ai_retrain_freq = request.POST["ai_retrain_freq"]

    strategy.save()
    logger.info("Strategy %s updated", strategy.name)
    return redirect("dashboard:strategies")


# ──────────────────────────────────────────────
# Risk Management Page
# ──────────────────────────────────────────────

def risk(request):
    """Risk configuration and live exposure monitoring."""
    risk_config = _get_risk_config()
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    trades_today = Trade.objects.filter(created_at__gte=today_start)
    daily_pnl = sum(t.realized_pnl for t in trades_today if t.realized_pnl) or Decimal("0.00")

    ctx = {
        **_base_context(),
        "active_page": "risk",
        "risk_config": risk_config,
        "daily_pnl": daily_pnl,
        "daily_drawdown_pct": Decimal("0.00"),  # Placeholder
        "open_positions": 0,  # Placeholder — will sync from Alpaca
        "trades_today_count": trades_today.count(),
        "risk_decisions": Trade.objects.all().order_by("-created_at")[:10],
    }
    return render(request, "dashboard/risk.html", ctx)


@require_POST
def update_risk(request):
    """HTMX: Update risk configuration parameters."""
    config = _get_risk_config()

    fields = [
        "max_daily_drawdown_pct", "max_total_drawdown_pct",
        "max_position_size_pct", "max_open_positions",
        "max_daily_trades", "daily_loss_limit",
    ]
    for field in fields:
        if field in request.POST:
            value = request.POST[field]
            if field in ("max_open_positions", "max_daily_trades"):
                setattr(config, field, int(value))
            else:
                setattr(config, field, Decimal(value))

    config.save()
    logger.info("Risk config updated")
    return redirect("dashboard:risk")


@require_POST
def kill_switch(request):
    """Toggle the emergency kill switch."""
    config = _get_risk_config()
    config.kill_switch_active = not config.kill_switch_active
    config.save()

    if config.kill_switch_active:
        logger.critical("🚨 KILL SWITCH ACTIVATED — ALL TRADING HALTED")
        # TODO: Call AlpacaClient.cancel_all_orders() and close_all_positions()
    else:
        logger.warning("✅ Kill switch deactivated — trading resumed")

    return HttpResponse(
        f'<span style="color:{"var(--red)" if config.kill_switch_active else "var(--green)"};">'
        f'{"⛔ TRADING HALTED" if config.kill_switch_active else "✅ Trading Active"}</span>'
    )


# ──────────────────────────────────────────────
# System Health Page
# ──────────────────────────────────────────────

def system(request):
    """System health monitoring — services, broker accounts, webhook stats."""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    # Webhook stats
    webhooks_24h = WebhookEvent.objects.filter(created_at__gte=last_24h)
    webhook_stats = {
        "received": webhooks_24h.count(),
        "dispatched": webhooks_24h.filter(status="dispatched").count(),
        "rejected": webhooks_24h.filter(status="rejected").count(),
        "errors": webhooks_24h.filter(status="error").count(),
    }

    # Connection checks (basic — will improve in Layer 1)
    mongo_connected = True  # If we got this far, Django/Djongo is connected
    redis_connected = _check_redis()
    alpaca_connected = bool(settings.BROKER_ALPACA_API_KEY)

    ctx = {
        **_base_context(),
        "active_page": "system",
        "mongo_connected": mongo_connected,
        "redis_connected": redis_connected,
        "alpaca_connected": alpaca_connected,
        "broker_accounts": BrokerAccount.objects.all(),
        "webhook_stats": webhook_stats,
        "django_version": django.get_version(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "settings_module": settings.SETTINGS_MODULE if hasattr(settings, "SETTINGS_MODULE") else "config.settings.development",
        "timezone": settings.TIME_ZONE,
        "server_time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }
    return render(request, "dashboard/system.html", ctx)


# ──────────────────────────────────────────────
# Prop Firm Accounts Page
# ──────────────────────────────────────────────

def prop_firms(request):
    """Prop firm accounts — track challenge progress and compliance."""
    ctx = {
        **_base_context(),
        "active_page": "prop_firms",
        "prop_accounts": PropFirmAccount.objects.filter(is_active=True),
    }
    return render(request, "dashboard/prop_firms.html", ctx)


# ──────────────────────────────────────────────
# Equity Curve API (Chart.js data)
# ──────────────────────────────────────────────

def equity_data_api(request):
    """JSON endpoint: cumulative P&L by date for the equity curve chart."""
    filled = Trade.objects.filter(
        status="filled", realized_pnl__isnull=False
    ).order_by("created_at")

    daily_pnl = defaultdict(Decimal)
    for trade in filled:
        day = trade.created_at.strftime("%Y-%m-%d")
        daily_pnl[day] += trade.realized_pnl

    if not daily_pnl:
        return JsonResponse({"labels": [], "data": []})

    sorted_days = sorted(daily_pnl.keys())
    daily_values = [float(daily_pnl[d]) for d in sorted_days]
    cumulative = list(accumulate(daily_values))

    return JsonResponse({
        "labels": sorted_days,
        "data": [round(v, 2) for v in cumulative],
    })


# ──────────────────────────────────────────────
# Accounts Page
# ──────────────────────────────────────────────

def accounts(request):
    """Broker accounts overview — view configured accounts and connection status."""
    ctx = {
        **_base_context(),
        "active_page": "accounts",
        "broker_accounts": BrokerAccount.objects.all(),
    }
    return render(request, "dashboard/accounts.html", ctx)


def _check_redis():
    """Quick Redis connectivity check."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return True
    except Exception:
        return False
