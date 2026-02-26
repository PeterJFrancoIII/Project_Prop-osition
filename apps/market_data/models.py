"""
Market data models.

Layer 0: Schema only — data ingestion pipelines come in Layer 1.
"""

from django.db import models


class OHLCVBar(models.Model):
    """
    OHLCV price bar for any asset (stocks, futures, crypto).

    Unified schema across all asset classes.
    """

    TIMEFRAME_CHOICES = [
        ("1m", "1 Minute"),
        ("5m", "5 Minutes"),
        ("15m", "15 Minutes"),
        ("1h", "1 Hour"),
        ("4h", "4 Hours"),
        ("1d", "1 Day"),
        ("1w", "1 Week"),
    ]

    symbol = models.CharField(max_length=20, db_index=True)
    timeframe = models.CharField(max_length=5, choices=TIMEFRAME_CHOICES, db_index=True)
    timestamp = models.DateTimeField(db_index=True)

    open = models.DecimalField(max_digits=15, decimal_places=6)
    high = models.DecimalField(max_digits=15, decimal_places=6)
    low = models.DecimalField(max_digits=15, decimal_places=6)
    close = models.DecimalField(max_digits=15, decimal_places=6)
    volume = models.BigIntegerField(default=0)

    # Metadata
    source = models.CharField(max_length=30, default="alpaca")

    class Meta:
        ordering = ["-timestamp"]
        unique_together = ["symbol", "timeframe", "timestamp"]
        verbose_name = "OHLCV Bar"
        verbose_name_plural = "OHLCV Bars"

    def __str__(self):
        return f"{self.symbol} {self.timeframe} {self.timestamp} | O:{self.open} H:{self.high} L:{self.low} C:{self.close}"


class NewsArticle(models.Model):
    """
    Stores news headlines and content for sentiment analysis.
    """
    symbol = models.CharField(max_length=20, db_index=True, blank=True, null=True, help_text="Specific ticker this news is about")
    source = models.CharField(max_length=50, db_index=True)
    url = models.URLField(max_length=500, unique=True, blank=True, null=True)
    headline = models.CharField(max_length=500)
    content = models.TextField(blank=True, null=True)
    published_at = models.DateTimeField(db_index=True)

    # Sentiment data
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=4, default=0.0, help_text="Range: -1.0 (Bearish) to 1.0 (Bullish)")
    sentiment_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.0)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "News Article"
        verbose_name_plural = "News Articles"

    def __str__(self):
        ticker_part = f"[{self.symbol}] " if self.symbol else ""
        return f"{ticker_part}{self.headline[:50]}"
