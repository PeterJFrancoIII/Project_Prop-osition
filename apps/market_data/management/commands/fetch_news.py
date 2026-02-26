import logging
import feedparser
from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil import parser as date_parser
from apps.market_data.models import NewsArticle
from apps.ai_brain.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)

# Publicly available RSS feeds
FEEDS = [
    "http://feeds.bbci.co.uk/news/business/rss.xml",
    "https://yahoo.com/news/rss/stock-market",
    "https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance",
]

class Command(BaseCommand):
    help = "Fetch news from RSS feeds and store them in the database with sentiment analysis."

    def add_arguments(self, parser):
        parser.add_argument("--ticker", type=str, help="Specific ticker to hunt for (simulated filter)")

    def handle(self, *args, **options):
        ticker = options.get("ticker")
        analyzer = SentimentAnalyzer()
        
        articles_added = 0

        self.stdout.write(self.style.NOTICE(f"Fetching news feeds... (Filtering for {ticker if ticker else 'All'})"))

        for feed_url in FEEDS:
            try:
                self.stdout.write(f"Parsing {feed_url}...")
                
                # Use requests to bypass User-Agent blocking
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                import requests
                response = requests.get(feed_url, headers=headers, timeout=10)
                
                feed = feedparser.parse(response.content)
                self.stdout.write(f"  Found {len(feed.entries)} entries.")
                
                for entry in feed.entries:
                    # Basic collision check by URL
                    url = entry.get("link", "")
                    if NewsArticle.objects.filter(url=url).exists():
                        continue

                    headline = entry.get("title", "")
                    content = entry.get("description", "") or entry.get("summary", "")
                    
                    # Sentiment analysis
                    full_text = f"{headline}. {content}"
                    sentiment = analyzer.analyze(full_text)

                    # Date parsing
                    pub_date = timezone.now()
                    if "published" in entry:
                        try:
                            pub_date = date_parser.parse(entry.get("published"))  # pyre-ignore
                        except:
                            pass

                    # Save
                    NewsArticle.objects.create(
                        symbol=ticker,
                        source=feed_url.split("/")[2],
                        url=url,
                        headline=headline,
                        content=content,
                        published_at=pub_date,
                        sentiment_score=sentiment["score"],
                        sentiment_confidence=sentiment["confidence"]
                    )
                    articles_added += 1

                    if articles_added >= 50:
                        break

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching {feed_url}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully added {articles_added} new articles."))
