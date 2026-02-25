"""
Backtesting engine — vectorized historical strategy simulation.

Usage:
    python manage.py backtest momentum_breakout --symbol AAPL --days 365
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.market_data.models import OHLCVBar
from apps.strategies.momentum_breakout import MomentumBreakout
from apps.strategies.mean_reversion import MeanReversion

logger = logging.getLogger(__name__)

# Strategy registry
STRATEGY_MAP = {
    "momentum_breakout": MomentumBreakout,
    "mean_reversion": MeanReversion,
}


class Command(BaseCommand):
    help = "Backtest a strategy against historical data"

    def add_arguments(self, parser):
        parser.add_argument(
            "strategy", type=str, choices=list(STRATEGY_MAP.keys()),
            help="Strategy name to backtest"
        )
        parser.add_argument(
            "--symbol", type=str, default="AAPL",
            help="Symbol to backtest (default: AAPL)"
        )
        parser.add_argument(
            "--days", type=int, default=365,
            help="Days of history to test (default: 365)"
        )
        parser.add_argument(
            "--equity", type=float, default=100000,
            help="Starting account equity (default: $100,000)"
        )
        parser.add_argument(
            "--config", type=str, default="{}",
            help="JSON config for strategy parameters"
        )

    def handle(self, *args, **options):
        import json

        strategy_name = options["strategy"]
        symbol = options["symbol"].upper()
        days = options["days"]
        starting_equity = Decimal(str(options["equity"]))

        try:
            config = json.loads(options["config"])
        except json.JSONDecodeError:
            config = {}

        self.stdout.write(
            f"\n{'='*60}\n"
            f"  BACKTEST: {strategy_name} on {symbol}\n"
            f"  Period: {days} days | Equity: ${starting_equity:,.2f}\n"
            f"{'='*60}\n"
        )

        # Fetch data
        bars = self._fetch_bars(symbol, days)
        if len(bars) < 50:
            self.stderr.write(
                self.style.ERROR(
                    f"Not enough data for {symbol} ({len(bars)} bars). "
                    f"Run: python manage.py fetch_market_data {symbol} --days {days}"
                )
            )
            return

        # Initialize strategy
        StrategyCls = STRATEGY_MAP[strategy_name]
        strategy = StrategyCls(config)

        # Run simulation
        results = self._simulate(strategy, symbol, bars, starting_equity)

        # Print report
        self._print_report(strategy_name, symbol, results, starting_equity)

    def _fetch_bars(self, symbol: str, days: int) -> list:
        """Fetch bars from OHLCVBar model."""
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

    def _simulate(
        self, strategy, symbol: str, bars: list, starting_equity: Decimal
    ) -> dict:
        """
        Vectorized backtest simulation.

        Walks through bars day-by-day, generates signals, simulates fills,
        and tracks portfolio equity.
        """
        equity = starting_equity
        position = Decimal("0")  # Shares held
        entry_price = Decimal("0")
        trades = []
        equity_curve = []
        peak_equity = starting_equity

        for i in range(50, len(bars)):
            bar_window = bars[:i + 1]
            current_price = Decimal(str(bars[i]["close"]))
            current_date = bars[i]["timestamp"]

            # Track equity
            unrealized = position * (current_price - entry_price) if position > 0 else Decimal("0")
            current_equity = equity + unrealized
            equity_curve.append({"date": current_date, "equity": float(current_equity)})

            # Peak tracking for max drawdown
            if current_equity > peak_equity:
                peak_equity = current_equity

            if position > 0:
                # Check exit
                exit_signal = strategy.check_exit(
                    symbol, entry_price, current_price, bar_window
                )
                if exit_signal.is_actionable:
                    # SELL
                    pnl = (current_price - entry_price) * position
                    equity += pnl + (entry_price * position)  # Return capital + P&L
                    trades.append({
                        "date": str(current_date),
                        "action": "sell",
                        "price": float(current_price),
                        "qty": float(position),
                        "pnl": float(pnl),
                        "reason": exit_signal.reason,
                    })
                    position = Decimal("0")
                    entry_price = Decimal("0")
            else:
                # Check entry
                signal = strategy.generate_signal(symbol, bar_window)
                if signal.is_actionable and signal.action == "buy":
                    # BUY
                    qty = strategy.calculate_position_size(symbol, current_price, equity)
                    cost = current_price * qty
                    if cost <= equity:
                        equity -= cost
                        position = qty
                        entry_price = current_price
                        trades.append({
                            "date": str(current_date),
                            "action": "buy",
                            "price": float(current_price),
                            "qty": float(qty),
                            "pnl": 0.0,
                            "reason": signal.reason,
                        })

        # Close any open position at final bar
        if position > 0:
            final_price = Decimal(str(bars[-1]["close"]))
            pnl = (final_price - entry_price) * position
            equity += pnl + (entry_price * position)
            trades.append({
                "date": str(bars[-1]["timestamp"]),
                "action": "sell (close)",
                "price": float(final_price),
                "qty": float(position),
                "pnl": float(pnl),
                "reason": "End of backtest — closing position",
            })

        # Calculate metrics
        final_equity = equity
        total_return = float((final_equity - starting_equity) / starting_equity * 100)
        winning = [t for t in trades if t["action"].startswith("sell") and t["pnl"] > 0]
        losing = [t for t in trades if t["action"].startswith("sell") and t["pnl"] < 0]
        sell_trades = [t for t in trades if t["action"].startswith("sell")]

        # Max drawdown
        max_dd = 0
        peak = float(starting_equity)
        for point in equity_curve:
            if point["equity"] > peak:
                peak = point["equity"]
            dd = (peak - point["equity"]) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        # Sharpe approximation (annualized, assuming daily returns)
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                prev = equity_curve[i - 1]["equity"]
                curr = equity_curve[i]["equity"]
                if prev > 0:
                    returns.append((curr - prev) / prev)
            if returns:
                avg_ret = sum(returns) / len(returns)
                variance = sum((r - avg_ret) ** 2 for r in returns) / len(returns)
                std_ret = variance ** 0.5
                sharpe = (avg_ret / std_ret * (252 ** 0.5)) if std_ret > 0 else 0
            else:
                sharpe = 0
        else:
            sharpe = 0

        return {
            "final_equity": float(final_equity),
            "total_return_pct": total_return,
            "total_trades": len(trades),
            "buy_trades": len([t for t in trades if t["action"] == "buy"]),
            "sell_trades": len(sell_trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(sell_trades) * 100 if sell_trades else 0,
            "total_pnl": sum(t["pnl"] for t in sell_trades),
            "avg_win": sum(t["pnl"] for t in winning) / len(winning) if winning else 0,
            "avg_loss": sum(t["pnl"] for t in losing) / len(losing) if losing else 0,
            "max_drawdown_pct": max_dd,
            "sharpe_ratio": sharpe,
            "trades": trades,
            "equity_curve": equity_curve,
            "bars_count": len(bars),
        }

    def _print_report(self, strategy_name: str, symbol: str, results: dict, starting_equity: Decimal):
        """Print formatted backtest report."""
        r = results

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n"
            f"  📊 BACKTEST RESULTS\n"
            f"{'='*60}\n"
        ))

        # Portfolio summary
        self.stdout.write(
            f"  Strategy:     {strategy_name}\n"
            f"  Symbol:       {symbol}\n"
            f"  Start Equity: ${float(starting_equity):>12,.2f}\n"
            f"  Final Equity: ${r['final_equity']:>12,.2f}\n"
            f"  Total Return: {r['total_return_pct']:>+11.2f}%\n"
            f"  Total P&L:    ${r['total_pnl']:>12,.2f}\n"
        )

        # Trade stats
        self.stdout.write(
            f"\n  {'─'*40}\n"
            f"  Total Trades: {r['total_trades']:>5}\n"
            f"  Wins:         {r['winning_trades']:>5}  ({r['win_rate']:.1f}%)\n"
            f"  Losses:       {r['losing_trades']:>5}\n"
            f"  Avg Win:      ${r['avg_win']:>12,.2f}\n"
            f"  Avg Loss:     ${r['avg_loss']:>12,.2f}\n"
        )

        # Risk metrics
        self.stdout.write(
            f"\n  {'─'*40}\n"
            f"  Max Drawdown: {r['max_drawdown_pct']:>8.2f}%\n"
            f"  Sharpe Ratio: {r['sharpe_ratio']:>8.2f}\n"
            f"  Bars Tested:  {r['bars_count']:>5}\n"
        )

        # Recent trades
        if r["trades"]:
            self.stdout.write(f"\n  {'─'*40}\n  RECENT TRADES (last 10):\n")
            for t in r["trades"][-10:]:
                pnl_str = f"${t['pnl']:+,.2f}" if t["pnl"] != 0 else ""
                action_color = self.style.SUCCESS if t["action"] == "buy" else self.style.WARNING
                self.stdout.write(
                    f"  {t['date'][:10]}  {action_color(t['action'].upper():>10s)}"
                    f"  {t['qty']:.0f} @ ${t['price']:.2f}  {pnl_str}\n"
                    f"               {t['reason']}\n"
                )

        self.stdout.write(f"\n{'='*60}\n")
