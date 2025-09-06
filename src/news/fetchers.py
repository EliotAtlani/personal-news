import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import feedparser
from asyncio_throttle import Throttler

# Try to import Event Registry - install with: pip install eventregistry
try:
    from eventregistry import EventRegistry, QueryArticlesIter

    EVENTREGISTRY_AVAILABLE = True
except ImportError:
    EVENTREGISTRY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Article:
    def __init__(
        self,
        title: str,
        description: str,
        url: str,
        source: str,
        published_at: datetime,
        content: str = "",
    ):
        self.title = title
        self.description = description
        self.url = url
        self.source = source
        self.published_at = published_at
        self.content = content
        self.relevance_score = 0.0

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "content": self.content,
            "relevance_score": self.relevance_score,
        }


class NewsAPIFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.throttler = Throttler(rate_limit=100, period=86400)  # 100 requests per day

    async def fetch_articles(
        self, topics: list[str], from_date: datetime = None
    ) -> list[Article]:
        """Fetch articles from NewsAPI for given topics."""
        if not from_date:
            from_date = datetime.now() - timedelta(days=1)

        articles = []

        async with aiohttp.ClientSession() as session:
            for topic in topics:
                await self.throttler.acquire()
                try:
                    print(self.base_url)
                    url = f"{self.base_url}/everything"
                    params = {
                        "q": topic,
                        "from": from_date.strftime("%Y-%m-%d"),
                        "sortBy": "relevancy",
                        "pageSize": 20,
                        "apiKey": self.api_key,
                    }

                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            for article_data in data.get("articles", []):
                                article = self._parse_newsapi_article(
                                    article_data, topic
                                )
                                if article:
                                    articles.append(article)
                        else:
                            logger.error(
                                f"NewsAPI error for topic {topic}: {response.status}"
                            )

                except Exception as e:
                    logger.error(f"Error fetching from NewsAPI for topic {topic}: {e}")

        return articles

    def _parse_newsapi_article(self, data: dict, topic: str) -> Optional[Article]:
        """Parse NewsAPI article data into Article object."""
        try:
            published_at = datetime.fromisoformat(
                data["publishedAt"].replace("Z", "+00:00")
            )
            return Article(
                title=data.get("title", ""),
                description=data.get("description", ""),
                url=data.get("url", ""),
                source=data.get("source", {}).get("name", "Unknown"),
                published_at=published_at,
                content=data.get("content", ""),
            )
        except Exception as e:
            logger.error(f"Error parsing NewsAPI article: {e}")
            return None


class GuardianFetcher:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://content.guardianapis.com"
        # Debug logging for API key
        if api_key:
            logger.info(f"Guardian API key initialized: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else api_key}")
        else:
            logger.warning("Guardian API key is None/empty")

    async def fetch_articles(
        self, topics: list[str], from_date: datetime = None
    ) -> list[Article]:
        """Fetch articles from The Guardian API."""
        if not from_date:
            from_date = datetime.now() - timedelta(days=1)

        articles = []

        async with aiohttp.ClientSession() as session:
            for topic in topics:
                try:
                    url = f"{self.base_url}/search"
                    params = {
                        "q": topic,
                        "from-date": from_date.strftime("%Y-%m-%d"),
                        "show-fields": "headline,trailText,webUrl,bodyText",
                        "order-by": "relevance",
                        "page-size": 20,
                    }

                    if self.api_key:
                        params["api-key"] = self.api_key

                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            for article_data in data.get("response", {}).get(
                                "results", []
                            ):
                                article = self._parse_guardian_article(article_data)
                                if article:
                                    articles.append(article)
                        else:
                            logger.error(
                                f"Guardian API error for topic {topic}: {response.status}"
                            )

                except Exception as e:
                    logger.error(f"Error fetching from Guardian for topic {topic}: {e}")

        return articles

    def _parse_guardian_article(self, data: dict) -> Optional[Article]:
        """Parse Guardian article data into Article object."""
        try:
            published_at = datetime.fromisoformat(
                data["webPublicationDate"].replace("Z", "+00:00")
            )
            fields = data.get("fields", {})

            return Article(
                title=fields.get("headline", data.get("webTitle", "")),
                description=fields.get("trailText", ""),
                url=data.get("webUrl", ""),
                source="The Guardian",
                published_at=published_at,
                content=fields.get("bodyText", ""),
            )
        except Exception as e:
            logger.error(f"Error parsing Guardian article: {e}")
            return None


class RSSFetcher:
    def __init__(self):
        self.feeds = {
            # General News Sources
            "bbc": "http://feeds.bbci.co.uk/news/rss.xml",
            "reuters": "http://feeds.reuters.com/reuters/topNews",
            # Geopolitics & World News
            "bbc-world": "http://feeds.bbci.co.uk/news/world/rss.xml",
            "reuters-world": "http://feeds.reuters.com/reuters/worldNews",
            "ap-news": "https://rsshub.app/ap/topics/apf-intlnews",
            "foreign-affairs": "https://www.foreignaffairs.com/rss.xml",
            "foreign-policy": "https://foreignpolicy.com/feed/",
            "defense-news": "https://www.defensenews.com/arc/outboundfeeds/rss/",
            "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
            "nyt-world": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "le-monde": "https://www.lemonde.fr/international/rss_full.xml",
            "economist": "https://www.economist.com/international/rss.xml",
            # Major Tech News
            "techcrunch": "http://feeds.feedburner.com/TechCrunch",
            "ars-technica": "http://feeds.arstechnica.com/arstechnica/index",
            "wired": "https://www.wired.com/feed/rss",
            "the-verge": "https://www.theverge.com/rss/index.xml",
            "engadget": "https://www.engadget.com/rss.xml",
            "venturebeat": "https://venturebeat.com/feed/",
            "techradar": "https://www.techradar.com/rss",
            "zdnet": "https://www.zdnet.com/news/rss.xml",
            "mit-tech-review": "https://www.technologyreview.com/feed/",
            # Developer Communities
            "hacker-news": "https://hnrss.org/frontpage",
            "github-trending": "https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml",
            "dev-to": "https://dev.to/feed",
            "stackoverflow-blog": "https://stackoverflow.blog/feed/",
            "freecodecamp": "https://www.freecodecamp.org/news/rss/",
            "product-hunt": "https://www.producthunt.com/feed/daily",
            # Medium Publications (Tech focused)
            "medium-programming": "https://medium.com/feed/topic/programming",
            "medium-software-engineering": "https://medium.com/feed/topic/software-engineering",
            "medium-technology": "https://medium.com/feed/topic/technology",
            "medium-artificial-intelligence": "https://medium.com/feed/topic/artificial-intelligence",
            "medium-web-development": "https://medium.com/feed/topic/web-development",
            "medium-data-science": "https://medium.com/feed/topic/data-science",
            "medium-javascript": "https://medium.com/feed/topic/javascript",
            "medium-python": "https://medium.com/feed/topic/python",
            "medium-machine-learning": "https://medium.com/feed/topic/machine-learning",
            "medium-startup": "https://medium.com/feed/topic/startup",
            # Premium Medium Publications
            "towards-data-science": "https://towardsdatascience.com/feed",
            "better-programming": "https://betterprogramming.pub/feed",
            "the-startup": "https://medium.com/feed/swlh",
            "hackernoon": "https://hackernoon.com/feed",
            "freecodecamp-medium": "https://medium.com/feed/free-code-camp",
            # Design & Frontend
            "smashing-magazine": "https://www.smashingmagazine.com/feed/",
            "css-tricks": "https://css-tricks.com/feed/",
            "a-list-apart": "https://alistapart.com/main/feed/",
            # Additional Quality Tech Sources
            "infoq": "https://feed.infoq.com/",
            "dzone": "https://feeds.dzone.com/home",
            "reddit-programming": "https://www.reddit.com/r/programming/.rss",
            "lobsters": "https://lobste.rs/rss",
            "indie-hackers": "https://www.indiehackers.com/feed.xml",
            # Cloud & DevOps
            "aws-blog": "https://aws.amazon.com/blogs/aws/feed/",
            "google-cloud-blog": "https://cloud.google.com/blog/rss/",
            "kubernetes-blog": "https://kubernetes.io/feed.xml",
            "docker-blog": "https://blog.docker.com/feed/",
            # Company Engineering Blogs
            "netflix-tech": "https://netflixtechblog.com/feed",
            "uber-engineering": "https://eng.uber.com/feed/",
            "airbnb-engineering": "https://medium.com/feed/airbnb-engineering",
            "dropbox-tech": "https://dropbox.tech/feed",
            "spotify-engineering": "https://engineering.atspotify.com/feed/",
            "slack-engineering": "https://slack.engineering/feed/",
        }

    async def fetch_articles(
        self, sources: list[str] = None, from_date: datetime = None
    ) -> list[Article]:
        """Fetch articles from RSS feeds."""
        if not sources:
            sources = list(self.feeds.keys())

        if not from_date:
            from_date = datetime.now() - timedelta(days=1)

        articles = []

        for source in sources:
            if source not in self.feeds:
                continue

            try:
                feed = feedparser.parse(self.feeds[source])
                for entry in feed.entries:
                    article = self._parse_rss_entry(entry, source, from_date)
                    if article:
                        articles.append(article)

            except Exception as e:
                logger.error(f"Error fetching RSS feed for {source}: {e}")

        return articles

    def _parse_rss_entry(
        self, entry, source: str, from_date: datetime
    ) -> Optional[Article]:
        """Parse RSS entry into Article object."""
        try:
            # Parse publication date
            published_at = datetime.now()
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published_at = datetime(*entry.updated_parsed[:6])

            # Filter by date
            if published_at < from_date:
                return None

            return Article(
                title=entry.get("title", ""),
                description=entry.get("summary", ""),
                url=entry.get("link", ""),
                source=source.replace("-", " ").title(),
                published_at=published_at,
                content=(
                    entry.get("content", [{}])[0].get("value", "")
                    if entry.get("content")
                    else ""
                ),
            )

        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None


class EventRegistryFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not EVENTREGISTRY_AVAILABLE:
            logger.warning(
                "EventRegistry not available - install with: pip install eventregistry"
            )
            self.er = None
        else:
            self.er = EventRegistry(apiKey=api_key)

    async def fetch_articles(
        self, topics: list[str], from_date: datetime = None
    ) -> list[Article]:
        """Fetch articles from Event Registry for given topics."""
        if not self.er:
            logger.warning("Event Registry not initialized")
            return []

        if not from_date:
            from_date = datetime.now() - timedelta(days=1)

        articles = []

        for topic in topics:
            try:
                # Use keyword search for topics
                query = {
                    "$query": {"keyword": topic, "lang": "eng"},
                    "$filter": {
                        "forceMaxDataTimeWindow": "7",  # Last 7 days
                        "dateStart": from_date.strftime("%Y-%m-%d"),
                        "dateEnd": datetime.now().strftime("%Y-%m-%d"),
                    },
                }

                q = QueryArticlesIter.initWithComplexQuery(query)

                # Fetch articles (limit to 20 per topic to avoid overloading)
                topic_articles = []
                for article_data in q.execQuery(self.er, maxItems=20):
                    article = self._parse_eventregistry_article(article_data, topic)
                    if article:
                        topic_articles.append(article)

                articles.extend(topic_articles)
                logger.info(
                    f"Event Registry fetched {len(topic_articles)} articles for topic '{topic}'"
                )

            except Exception as e:
                logger.error(
                    f"Error fetching from Event Registry for topic {topic}: {e}"
                )

        return articles

    def _parse_eventregistry_article(self, data: dict, topic: str) -> Optional[Article]:
        """Parse Event Registry article data into Article object."""
        try:
            # Event Registry article structure
            published_str = data.get("dateTime", "")
            if published_str:
                published_at = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                )
            else:
                published_at = datetime.now()

            return Article(
                title=data.get("title", ""),
                description=(
                    data.get("body", "")[:300] + "..."
                    if len(data.get("body", "")) > 300
                    else data.get("body", "")
                ),
                url=data.get("url", ""),
                source=data.get("source", {}).get("title", "Unknown"),
                published_at=published_at,
                content=data.get("body", ""),
            )
        except Exception as e:
            logger.error(f"Error parsing Event Registry article: {e}")
            return None


class NewsFetcher:
    def __init__(
        self, newsapi_key: str, guardian_key: str = None, eventregistry_key: str = None
    ):
        self.newsapi = NewsAPIFetcher(newsapi_key) if newsapi_key else None
        self.guardian = GuardianFetcher(guardian_key)
        self.rss = RSSFetcher()
        self.eventregistry = (
            EventRegistryFetcher(eventregistry_key) if eventregistry_key else None
        )

    async def fetch_all_articles(
        self, topics: list[str], sources: list[str] = None, from_date: datetime = None
    ) -> list[Article]:
        """Fetch articles from all available sources."""
        all_articles = []

        # Fetch from different sources concurrently
        tasks = []

        # Skip NewsAPI for now due to 401 errors
        # if self.newsapi:
        #     tasks.append(self.newsapi.fetch_articles(topics, from_date))

        # Skip EventRegistry due to installation issues
        # if self.eventregistry:
        #     tasks.append(self.eventregistry.fetch_articles(topics, from_date))

        tasks.append(self.guardian.fetch_articles(topics, from_date))
        tasks.append(self.rss.fetch_articles(sources, from_date))

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_articles.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in news fetching task: {result}")

        except Exception as e:
            logger.error(f"Error in concurrent news fetching: {e}")

        # Limit articles per source to max 3
        limited_articles = self._limit_articles_per_source(all_articles, max_per_source=3)
        
        return limited_articles
    
    def _limit_articles_per_source(self, articles: list[Article], max_per_source: int = 3) -> list[Article]:
        """Limit the number of articles per source to avoid overwhelming from one source."""
        source_counts = {}
        limited_articles = []
        
        # Sort articles by published date (newest first) to get best articles from each source
        # Handle both timezone-aware and timezone-naive datetimes
        def get_sort_key(article):
            dt = article.published_at
            if dt.tzinfo is None:
                # Make naive datetime timezone-aware (assume UTC)
                from datetime import timezone
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        
        sorted_articles = sorted(articles, key=get_sort_key, reverse=True)
        
        for article in sorted_articles:
            source_count = source_counts.get(article.source, 0)
            if source_count < max_per_source:
                limited_articles.append(article)
                source_counts[article.source] = source_count + 1
        
        logger.info(f"Limited articles: {len(articles)} -> {len(limited_articles)}")
        for source, count in source_counts.items():
            logger.info(f"  {source}: {count} articles")
            
        return limited_articles
