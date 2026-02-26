import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from apps.market_data.models import OHLCVBar
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class RegimeDetector:
    """
    Market Regime Detection Engine.
    
    Identifies if the market is trending, ranging, or highly volatile.
    Uses 'SPY' (or a configured benchmark) to determine the macro environment.
    """
    
    def __init__(self, benchmark_ticker: str = "SPY"):
        self.benchmark = benchmark_ticker

    def get_market_regime(self, date_cutoff: Optional[datetime] = None, lookback_days: int = 60) -> Dict[str, Any]:
        """
        Determines the current market regime based on benchmark price action.
        Returns a dict containing 'trend', 'volatility', and 'is_crash_mode'.
        """
        cutoff = date_cutoff or timezone.now()
        start = cutoff - timedelta(days=lookback_days)
        
        bars = OHLCVBar.objects.filter(
            symbol=self.benchmark,
            timeframe="1d",
            timestamp__gte=start,
            timestamp__lte=cutoff
        ).order_by("timestamp")
        
        if bars.count() < 20: # Need at least ~20 days to make a determination
            return {
                "trend": "unknown",         # bullish, bearish, ranging
                "volatility": "neutral",    # high, low, neutral
                "is_crash_mode": False
            }
            
        closes = [float(b.close) for b in bars]
        df = pd.DataFrame({"close": closes})
        
        # Calculate trailing returns and standard deviations
        returns = df["close"].pct_change().dropna()
        volatility_annualized = returns.std() * np.sqrt(252)
        
        # Trend detection via simple Moving Average structure (e.g. 20-day vs 50-day)
        if len(closes) >= 50:
            sma20 = df["close"].rolling(window=20).mean().iloc[-1]
            sma50 = df["close"].rolling(window=50).mean().iloc[-1]
            current = df["close"].iloc[-1]
            
            if current > sma20 and sma20 > sma50:
                trend = "bullish"
            elif current < sma20 and sma20 < sma50:
                trend = "bearish"
            else:
                trend = "ranging"
        else:
            # Fallback if we only have 20-49 days
            sma20 = df["close"].rolling(window=20).mean().iloc[-1]
            current = df["close"].iloc[-1]
            trend = "bullish" if current > sma20 else "bearish"
            
        # Volatility Classification
        if volatility_annualized > 0.30: # 30%+ annualized standard dev is very high for SPY
            vol_state = "high"
        elif volatility_annualized < 0.15: # <15% is low volatility trending
            vol_state = "low"
        else:
            vol_state = "neutral"
            
        # Crash condition
        # e.g., market is down more than 10% in last 20 days and vol is high
        recent_drop = (df["close"].iloc[-1] / df["close"].iloc[-20]) - 1
        is_crash = (recent_drop < -0.10) and vol_state == "high"

        return {
            "trend": trend,
            "volatility": vol_state,
            "is_crash_mode": is_crash,
            "annualized_volatility": float(volatility_annualized),
            "benchmark": self.benchmark
        }
