"""
Dashboard view tests.

Tests all dashboard pages return 200, HTMX partials return fragments,
kill switch and strategy toggles work, and risk config saves correctly.
"""

from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from apps.dashboard.models import Strategy
from apps.risk_management.models import RiskConfig


class DashboardPageTests(TestCase):
    """Every dashboard page must return 200 on GET."""

    def setUp(self):
        self.client = Client()
        RiskConfig.objects.get_or_create(name="default")

    def test_overview_page(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Overview")

    def test_trades_page(self):
        response = self.client.get(reverse("dashboard:trades"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trade History")

    def test_activity_page(self):
        response = self.client.get(reverse("dashboard:activity"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Activity Log")

    def test_strategies_page(self):
        response = self.client.get(reverse("dashboard:strategies"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Strategies")

    def test_risk_page(self):
        response = self.client.get(reverse("dashboard:risk"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Risk Management")

    def test_system_page(self):
        response = self.client.get(reverse("dashboard:system"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Health")

    def test_accounts_page(self):
        response = self.client.get(reverse("dashboard:accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Broker Accounts")

    def test_equity_data_api(self):
        response = self.client.get(reverse("dashboard:equity-data"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("labels", data)
        self.assertIn("data", data)

    def test_prop_firms_page(self):
        response = self.client.get(reverse("dashboard:prop-firms"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prop Firm")


class HTMXPartialTests(TestCase):
    """HTMX partial endpoints return HTML fragments, not full pages."""

    def setUp(self):
        self.client = Client()
        RiskConfig.objects.get_or_create(name="default")

    def test_stats_partial_no_full_page(self):
        response = self.client.get(reverse("dashboard:overview-stats"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Fragment should contain stat-card but NOT the full page doctype
        self.assertNotIn("<!DOCTYPE", content)
        self.assertIn("stat-card", content)

    def test_trades_partial_no_full_page(self):
        response = self.client.get(reverse("dashboard:recent-trades"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("<!DOCTYPE", content)

    def test_activity_partial_no_full_page(self):
        response = self.client.get(reverse("dashboard:recent-activity"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("<!DOCTYPE", content)


class KillSwitchTests(TestCase):
    """Kill switch toggle works correctly."""

    def setUp(self):
        self.client = Client()
        self.config, _ = RiskConfig.objects.get_or_create(name="default")

    def test_kill_switch_activates(self):
        self.assertFalse(self.config.kill_switch_active)
        response = self.client.post(reverse("dashboard:kill-switch"))
        self.assertEqual(response.status_code, 200)
        self.config.refresh_from_db()
        self.assertTrue(self.config.kill_switch_active)

    def test_kill_switch_deactivates(self):
        self.config.kill_switch_active = True
        self.config.save()
        response = self.client.post(reverse("dashboard:kill-switch"))
        self.assertEqual(response.status_code, 200)
        self.config.refresh_from_db()
        self.assertFalse(self.config.kill_switch_active)


class StrategyToggleTests(TestCase):
    """Strategy toggle works correctly."""

    def setUp(self):
        self.client = Client()
        RiskConfig.objects.get_or_create(name="default")
        self.strategy = Strategy.objects.create(
            name="Test Momentum", is_active=False
        )

    def test_toggle_activates_strategy(self):
        self.assertFalse(self.strategy.is_active)
        response = self.client.post(
            reverse("dashboard:toggle-strategy", args=[self.strategy.id])
        )
        self.assertEqual(response.status_code, 302)  # Redirect after toggle
        self.strategy.refresh_from_db()
        self.assertTrue(self.strategy.is_active)


class RiskConfigUpdateTests(TestCase):
    """Risk configuration updates save correctly."""

    def setUp(self):
        self.client = Client()
        self.config, _ = RiskConfig.objects.get_or_create(name="default")

    def test_update_risk_params(self):
        response = self.client.post(reverse("dashboard:update-risk"), {
            "max_daily_drawdown_pct": "3.5",
            "max_position_size_pct": "5.0",
            "max_open_positions": "8",
            "max_daily_trades": "15",
        })
        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertEqual(self.config.max_daily_drawdown_pct, Decimal("3.5"))
        self.assertEqual(self.config.max_open_positions, 8)
