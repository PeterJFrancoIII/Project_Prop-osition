import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict

from django.core.management.base import BaseCommand
from apps.market_data.models import OHLCVBar
from apps.market_data.management.commands.run_strategies import STRATEGY_CLASSES
import itertools

logger = logging.getLogger(__name__)

# Basic parameter grid bounds for supported strategies
STRATEGY_GRIDS = {
    "momentum_breakout": {
        "rsi_period": [10, 14, 21],
        "rsi_overbought": [65, 70, 75],
        "volume_ma_period": [10, 20],
        "stop_loss_pct": [0.03, 0.05, 0.08],
        "take_profit_pct": [0.05, 0.10, 0.15],
    },
    "mean_reversion": {
        "bb_period": [14, 20, 30],
        "bb_std": [2.0, 2.5],
        "rsi_oversold": [25, 30, 35],
        "stop_loss_pct": [0.02, 0.04, 0.06],
        "take_profit_pct": [0.04, 0.08, 0.12],
    },
}


class Command(BaseCommand):
    help = "Run a grid search parameter optimization backtest for a strategy."

    def add_arguments(self, parser):
        parser.add_argument("strategy", type=str, help="Strategy name")
        parser.add_argument("symbol", type=str, help="Stock ticker symbol")
        parser.add_argument("--days", type=int, default=365, help="Days of history to use")
        parser.add_argument("--equity", type=float, default=10000.0, help="Starting equity")

    def handle(self, *args, **options):
        strategy_name = options["strategy"]
        symbol = options["symbol"].upper()
        days = options["days"]
        starting_equity = Decimal(str(options["equity"]))

        if strategy_name not in STRATEGY_CLASSES:
            self.stdout.write(self.style.ERROR(f"Unknown strategy: {strategy_name}"))
            return

        if strategy_name not in STRATEGY_GRIDS:
            self.stdout.write(self.style.ERROR(f"No optimization grid defined for {strategy_name}"))
            return

        self.stdout.write(f"\n🚀 Running Optimizer for {strategy_name} on {symbol}")
        
        # 1. Fetch data
        bars = self._fetch_bars(symbol, days)
        if len(bars) < 50:
            self.stderr.write(self.style.ERROR(f"Not enough data for {symbol} ({len(bars)} bars)."))
            return

        # 2. Build parameter grid
        grid = STRATEGY_GRIDS[strategy_name]
        keys = list(grid.keys())
        values = list(grid.values())
        permutations = list(itertools.product(*values))
        
        self.stdout.write(f"Testing {len(permutations)} total parameter combinations...\n")

        StrategyCls = STRATEGY_CLASSES[strategy_name]
        
        best_cagr = -999.0
        best_config = None
        best_results = {}

        # 3. Import simulation from the backtester dynamically to reuse the engine
        from apps.market_data.management.commands.backtest import Command as BacktestCommand
        bt_engine = BacktestCommand()

        count = 0
        for combo in permutations:
            count += 1
            config = dict(zip(keys, combo))
            # The backtester expects stop_loss/take_profit inside config as strings/floats
            # and instantiated directly
            strat_instance = StrategyCls(config)
            
            results = bt_engine._simulate(strat_instance, symbol, bars, starting_equity)
            cagr = results.get("cagr_pct", 0.0)
            
            # Print progress every 10
            if count % 10 == 0:
                self.stdout.write(f"Processed {count}/{len(permutations)}...")

            if cagr > best_cagr:
                best_cagr = cagr
                best_config = config
                best_results = results

        if not best_config:
            self.stdout.write(self.style.ERROR("Optimization failed to find profitable combinations."))
            return

        self.stdout.write(self.style.SUCCESS("\n🏆 OPTIMIZATION COMPLETE 🏆"))
        self.stdout.write(f"Best CAGR: {best_cagr:.2f}%")
        self.stdout.write(f"Win Rate:  {best_results.get('win_rate_pct', 0):.2f}%")
        self.stdout.write(f"Max DD:    {best_results.get('max_drawdown_pct', 0):.2f}%")
        self.stdout.write(f"Trades:    {best_results.get('total_trades', 0)}")
        self.stdout.write(f"\nOptimal Parameter Configuration:")
        self.stdout.write(json.dumps(best_config, indent=2))

    def _fetch_bars(self, symbol: str, days: int) -> list:
        end = datetime.now()
        start = end - timedelta(days=days)

        bars = OHLCVBar.objects.filter(
            symbol=symbol, timeframe="1d",
            timestamp__gte=start,
        ).order_by("timestamp")

        return [
            {
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": b.volume,
                "timestamp": b.timestamp,
            }
            for b in bars
        ]
