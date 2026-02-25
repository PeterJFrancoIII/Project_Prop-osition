"""
Fetch historical OHLCV market data via yfinance.

Usage:
    python manage.py fetch_market_data AAPL --days 365
    python manage.py fetch_market_data AAPL MSFT GOOGL --days 30 --timeframe 1d
"""

import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from apps.market_data.models import OHLCVBar

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch historical OHLCV data from yfinance and store in OHLCVBar"

    def add_arguments(self, parser):
        parser.add_argument(
            "symbols", nargs="+", type=str,
            help="Stock ticker symbols (e.g., AAPL MSFT GOOGL)"
        )
        parser.add_argument(
            "--days", type=int, default=365,
            help="Number of days of history to fetch (default: 365)"
        )
        parser.add_argument(
            "--timeframe", type=str, default="1d",
            choices=["1m", "5m", "15m", "1h", "1d", "1w"],
            help="Bar timeframe (default: 1d)"
        )

    def handle(self, *args, **options):
        try:
            import yfinance as yf
        except ImportError:
            self.stderr.write(
                self.style.ERROR(
                    "yfinance is not installed. Run: pip install yfinance"
                )
            )
            return

        symbols = [s.upper() for s in options["symbols"]]
        days = options["days"]
        timeframe = options["timeframe"]

        # Map our timeframe format to yfinance interval
        yf_interval_map = {
            "1m": "1m", "5m": "5m", "15m": "15m",
            "1h": "1h", "1d": "1d", "1w": "1wk",
        }
        yf_interval = yf_interval_map[timeframe]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        total_created = 0
        total_skipped = 0

        for symbol in symbols:
            self.stdout.write(f"Fetching {symbol} ({timeframe}, {days} days)...")

            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    interval=yf_interval,
                )

                if df is None or df.empty:
                    self.stdout.write(
                        self.style.WARNING(f"  No data returned for {symbol}")
                    )
                    continue

                created = 0
                skipped = 0

                for timestamp, row in df.iterrows():
                    _, was_created = OHLCVBar.objects.get_or_create(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=timestamp,
                        defaults={
                            "open": row["Open"],
                            "high": row["High"],
                            "low": row["Low"],
                            "close": row["Close"],
                            "volume": int(row["Volume"]),
                            "source": "yfinance",
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        skipped += 1

                total_created += created
                total_skipped += skipped

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {symbol}: {created} bars created, {skipped} already existed"
                    )
                )

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"  Error fetching {symbol}: {e}")
                )
                logger.error("Market data fetch failed for %s: %s", symbol, e, exc_info=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Total: {total_created} created, {total_skipped} skipped."
            )
        )
