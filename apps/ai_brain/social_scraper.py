import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SocialScraper:
    """
    Scrapes retail sentiment from social platforms like Reddit and StockTwits.
    """
    
    def __init__(self):
        self.session = requests.Session()
        # Reddit requires a custom User-Agent to avoid getting instantly blocked
        self.session.headers.update({
            "User-Agent": "macOS:AutoTraderAI:v1.0 (by /u/AutoTraderDev)"
        })

    def get_reddit_sentiment_texts(self, symbol: str, limit: int = 25) -> list[str]:
        """
        Fetches recent comments/titles mentioning the symbol from WallStreetBets or investing subreddits.
        """
        texts = []
        # Search across popular financial subreddits
        url = f"https://www.reddit.com/r/wallstreetbets/search.json?q={symbol}&sort=new&restrict_sr=on&limit={limit}"
        
        try:
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    title = post.get("title", "")
                    selftext = post.get("selftext", "")
                    # Combine title and body text
                    if title:
                        texts.append(title)
                    if selftext and len(selftext) < 500: # avoid massive walls of text
                        texts.append(selftext)
            else:
                logger.warning(f"Reddit API returned {resp.status_code} for {symbol}")
        except Exception as e:
            logger.error(f"Failed to fetch Reddit data for {symbol}: {e}")
            
        return texts

    def get_stocktwits_sentiment_texts(self, symbol: str, limit: int = 30) -> list[str]:
        """
        Fetches recent messages from StockTwits for a given symbol.
        """
        texts = []
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json?limit={limit}"
        
        try:
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                messages = data.get("messages", [])
                for msg in messages:
                    body = msg.get("body", "")
                    if body:
                        texts.append(body)
            else:
                logger.warning(f"StockTwits API returned {resp.status_code} for {symbol}")
        except Exception as e:
            logger.error(f"Failed to fetch StockTwits data for {symbol}: {e}")
            
        return texts

    def get_aggregate_social_texts(self, symbol: str) -> list[str]:
        """
        Combines texts from multiple social platforms.
        """
        reddit_texts = self.get_reddit_sentiment_texts(symbol)
        stocktwits_texts = self.get_stocktwits_sentiment_texts(symbol)
        
        return reddit_texts + stocktwits_texts
