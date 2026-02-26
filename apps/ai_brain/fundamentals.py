import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class FundamentalAnalyzer:
    """
    Fundamental Data Engine.
    
    Responsible for fetching and parsing:
      - Analyst rating consensus
      - Earnings surprise history
      - Valuation metrics (P/E, forward P/E, PEG)
      - Insider trading (mocked/stubbed for now without specific SEC API keys)
    """

    def __init__(self):
        try:
            import yfinance as yf
            self.yf = yf
        except ImportError:
            self.yf = None
            logger.warning("yfinance not installed. Fundamental analyzer will run in degraded mode.")

    def get_analyst_consensus(self, ticker: str) -> Dict[str, Any]:
        """
        Fetches the latest analyst recommendations and consensus out of 5.
        """
        if not self.yf:
            return {"consensus": "HOLD", "target_price": 0.0, "score": 3.0}

        try:
            stock = self.yf.Ticker(ticker)
            info = stock.info
            
            # yfinance info dict usually has recommendationKey and targetMeanPrice
            return {
                "consensus": info.get("recommendationKey", "hold").upper(),
                "target_price": info.get("targetMeanPrice", 0.0),
                "current_price": info.get("currentPrice", 0.0),
                "score": info.get("recommendationMean", 3.0) # 1=Strong Buy, 5=Sell
            }
        except Exception as e:
            logger.error(f"Error fetching analyst consensus for {ticker}: {e}")
            return {"consensus": "HOLD", "target_price": 0.0, "score": 3.0}

    def get_valuation_metrics(self, ticker: str) -> Dict[str, float]:
        """
        Fetches valuation multiples.
        """
        if not self.yf:
            return {"trailing_pe": 0.0, "forward_pe": 0.0, "peg_ratio": 0.0, "price_to_book": 0.0}

        try:
            stock = self.yf.Ticker(ticker)
            info = stock.info
            
            return {
                "trailing_pe": info.get("trailingPE", 0.0),
                "forward_pe": info.get("forwardPE", 0.0),
                "peg_ratio": info.get("pegRatio", 0.0),
                "price_to_book": info.get("priceToBook", 0.0)
            }
        except Exception as e:
            logger.error(f"Error fetching valuation for {ticker}: {e}")
            return {"trailing_pe": 0.0, "forward_pe": 0.0, "peg_ratio": 0.0, "price_to_book": 0.0}

    def get_earnings_surprise(self, ticker: str) -> Dict[str, Any]:
        """
        Checks the most recent earnings surprise drift.
        """
        if not self.yf:
            return {"last_surprise_pct": 0.0, "drift_signal": "neutral"}
            
        try:
            stock = self.yf.Ticker(ticker)
            # Earnings dates might have surprise info
            earn = stock.earnings_dates
            if earn is not None and not earn.empty:
                # Find the most recent reported earnings
                import pandas as pd
                past_earnings = earn[earn.index < pd.Timestamp.now(tz=earn.index.tz)]
                if not past_earnings.empty:
                    last_report = past_earnings.iloc[0]
                    surprise = last_report.get('Surprise(%)', 0.0)
                    
                    signal = "bullish" if surprise > 0.05 else "bearish" if surprise < -0.05 else "neutral"
                    return {
                        "last_surprise_pct": float(surprise),
                        "drift_signal": signal
                    }
            return {"last_surprise_pct": 0.0, "drift_signal": "neutral"}
        except Exception as e:
            logger.error(f"Error fetching earnings surprise for {ticker}: {e}")
            return {"last_surprise_pct": 0.0, "drift_signal": "neutral"}
