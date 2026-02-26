import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader_ready = True
except ImportError:
    vader_ready = False
    logger.warning("vaderSentiment not installed. Using basic keyword sentiment fallback.")

try:
    from textblob import TextBlob
    textblob_ready = True
except ImportError:
    textblob_ready = False
    logger.warning("textblob not installed. Using basic keyword sentiment fallback.")


class SentimentAnalyzer:
    """
    Unified analyzer for financial text (news, social media).
    """

    def __init__(self):
        if vader_ready:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None

    def analyze(self, text: str) -> dict:
        """
        Returns sentiment score (-1 to 1) and confidence.
        """
        if not text:
            return {"score": 0.0, "confidence": 0.0, "method": "none"}

        # 1. Try VADER (best for short social text/news headlines)
        if self.vader:
            vs = self.vader.polarity_scores(text)
            # VADER compound score is -1 to 1
            return {
                "score": float(vs["compound"]),
                "confidence": 0.8,
                "method": "vader"
            }

        # 2. Try TextBlob fallback
        if textblob_ready:
            blob = TextBlob(text)
            return {
                "score": float(blob.sentiment.polarity),
                "confidence": 0.6,
                "method": "textblob"
            }

        # 3. Simple Keyword Fallback (Last Resort)
        return self._keyword_fallback(text)

    def _keyword_fallback(self, text: str) -> dict:
        text = text.lower()
        bullish = ["bullish", "upgrade", "buy", "growth", "positive", "beat", "higher", "profit", "surge", "gain"]
        bearish = ["bearish", "downgrade", "sell", "decline", "negative", "miss", "lower", "loss", "crash", "drop"]

        score = 0.0
        words = text.split()
        for word in words:
            if word in bullish:
                score += 0.2
            elif word in bearish:
                score -= 0.2
        
        normalized_score = max(min(score, 1.0), -1.0)
        return {
            "score": normalized_score,
            "confidence": 0.3,
            "method": "keyword_fallback"
        }
