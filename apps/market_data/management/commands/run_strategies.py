"""
Strategy Runner — scans active strategies and dispatches signals.

Intended to run as a periodic task (Celery beat or cron):
    python manage.py run_strategies

For each active strategy:
  1. Fetch latest OHLCV bars
  2. Generate signal
  3. If actionable, dispatch through the execution pipeline
  4. Log results
"""

import logging
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.dashboard.models import Strategy
from apps.execution_engine.executor import execute_signal
from apps.strategies.momentum_breakout import MomentumBreakout
from apps.strategies.mean_reversion import MeanReversion
from apps.strategies.sector_rotation import SectorRotation
from apps.strategies.smart_dca import SmartDCA
from apps.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)

# Map strategy name → class
STRATEGY_CLASSES = {
    "momentum_breakout": MomentumBreakout,
    "mean_reversion": MeanReversion,
    "sector_rotation": SectorRotation,
    "smart_dca": SmartDCA,
}


class Command(BaseCommand):
    help = "Run all active strategies and dispatch signals"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print signals without executing trades"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        active_strategies = Strategy.objects.filter(is_active=True)

        if not active_strategies.exists():
            self.stdout.write(self.style.WARNING("No active strategies found."))
            return

        self.stdout.write(
            f"\n🤖 Strategy Runner — {active_strategies.count()} active strategies\n"
            f"{'='*50}\n"
        )

        # Determine total portfolio equity to allocate
        total_equity = Decimal("100000")
        try:
            from apps.broker_connector.alpaca_client import AlpacaClient
            client = AlpacaClient()
            acct = client.get_account()
            total_equity = Decimal(str(acct["equity"]))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Broker connection failed: {e}. Defaulting to $100k test equity."))
            
        from apps.risk_management.portfolio_allocator import PortfolioAllocator
        allocator = PortfolioAllocator(total_equity)
        strategy_allocations = allocator.get_strategy_allocations()

        for db_strategy in active_strategies:
            allocated_base = strategy_allocations.get(db_strategy.name, Decimal("0"))
            if allocated_base <= 0:
                self.stdout.write(self.style.WARNING(f"  ⚠️  {db_strategy.name}: $0 capital allocated (Risk Parity skipped)"))
                continue
                
            self._run_strategy(db_strategy, dry_run, allocated_base)

        self.stdout.write(self.style.SUCCESS("\n✅ Strategy run complete.\n"))

    def _run_strategy(self, db_strategy: Strategy, dry_run: bool, allocated_equity: Decimal):
        """Run a single strategy for all its configured symbols."""
        # Look up strategy class
        # Try matching by strategy name convention, or fall back to custom_params
        strategy_type = db_strategy.custom_params.get("strategy_type", "")
        StrategyCls = STRATEGY_CLASSES.get(strategy_type)

        if not StrategyCls:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠️  {db_strategy.name}: no/invalid strategy_type in custom_params "
                    f"(supported: {', '.join(STRATEGY_CLASSES.keys())})"
                )
            )
            return

        # Initialize strategy with DB config
        config = db_strategy.custom_params.copy()
        config["stop_loss_pct"] = float(db_strategy.stop_loss_pct)
        config["take_profit_pct"] = float(db_strategy.take_profit_pct)
        strategy = StrategyCls(config)

        symbols = db_strategy.symbols or []
        if not symbols:
            self.stdout.write(
                self.style.WARNING(f"  ⚠️  {db_strategy.name}: no symbols configured")
            )
            return

        self.stdout.write(f"\n  📈 {db_strategy.name} [{strategy_type}]")
        self.stdout.write(f"     Symbols: {', '.join(symbols)}")

        for ticker in symbols:
            try:
                bars = strategy.get_bars(ticker, limit=250)
                if len(bars) < 50:
                    self.stdout.write(
                        f"     {ticker}: skip (only {len(bars)} bars, need 50+)"
                    )
                    continue

                signal = strategy.generate_signal(ticker, bars)
                signal = strategy.apply_ai_filters(signal)
                signal = strategy.apply_fundamental_filters(signal)
                signal = strategy.apply_regime_filters(signal)

                if signal.is_actionable:
                    # Calculate position size
                    # Use specific allocator-assigned equity slice, not total account equity
                    # (Preventing massive over-leverage if 5+ strats all fire at once)
                    equity = allocated_equity

                    qty = strategy.calculate_position_size(
                        ticker, signal.price, equity
                    )
                    signal.quantity = qty
                    signal = strategy.apply_kelly_sizing(signal, equity)
                    qty = signal.quantity

                    if qty <= 0:
                        continue # Blocked by Kelly (Negative Edge / Zero Risk)

                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"     {ticker}: 🔥 {signal.action.upper()} "
                                f"{qty} @ ${signal.price} (DRY RUN)\n"
                                f"              Reason: {signal.reason}"
                            )
                        )
                    else:
                        # Dispatch through execution pipeline
                        trades = execute_signal(signal.to_dict())
                        trade_statuses = ", ".join([f"{t.broker_account_id or 'default'}:{t.status}" for t in trades])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"     {ticker}: 🔥 {signal.action.upper()} "
                                f"{qty} @ ${signal.price} → [{trade_statuses}]\n"
                                f"              Reason: {signal.reason}"
                            )
                        )
                else:
                    self.stdout.write(f"     {ticker}: ⏸️  HOLD ({signal.reason})")

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"     {ticker}: ❌ Error — {e}")
                )
                logger.error("Strategy runner error for %s/%s: %s", db_strategy.name, ticker, e, exc_info=True)
