import logging
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher

from src.news.fetchers import Article

logger = logging.getLogger(__name__)


class ContentFilter:
    def __init__(self, min_relevance_score: float = 0.6):
        self.min_relevance_score = min_relevance_score
        self.seen_urls: set[str] = set()
        self.seen_titles: set[str] = set()

    def filter_articles(
        self, articles: list[Article], topics: list[str]
    ) -> list[Article]:
        """Apply all filters to articles."""
        filtered = []

        for article in articles:
            # Skip if duplicate
            if self._is_duplicate(article):
                continue

            # Calculate relevance score
            article.relevance_score = self._calculate_relevance(article, topics)

            # Skip if relevance too low
            if article.relevance_score < self.min_relevance_score:
                continue

            # Skip if content quality is poor
            if not self._has_good_content_quality(article):
                continue

            filtered.append(article)
            self.seen_urls.add(article.url)
            self.seen_titles.add(article.title.lower().strip())

        # Sort by relevance score and recency (handle timezone-aware comparison)
        def sort_key(article):
            published_at = article.published_at
            # Make timezone-aware if naive
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=UTC)
            return (article.relevance_score, published_at)

        filtered.sort(key=sort_key, reverse=True)

        return filtered

    def _is_duplicate(self, article: Article) -> bool:
        """Check if article is a duplicate."""
        # Check URL
        if article.url in self.seen_urls:
            return True

        # Check title similarity
        title_lower = article.title.lower().strip()
        for seen_title in self.seen_titles:
            similarity = SequenceMatcher(None, title_lower, seen_title).ratio()
            if similarity > 0.85:  # 85% similarity threshold
                return True

        return False

    def _calculate_relevance(self, article: Article, topics: list[str]) -> float:
        """Calculate relevance score based on topic keywords."""
        score = 0.0
        total_checks = 0

        # Combine title, description, and content for analysis
        text = f"{article.title} {article.description} {article.content}".lower()

        for topic in topics:
            topic_words = topic.lower().split()
            topic_matches = 0

            for word in topic_words:
                # Exact word match
                if word in text:
                    topic_matches += 1

                # Partial matches for compound words
                pattern = rf"\b{re.escape(word)}\w*"
                if re.search(pattern, text):
                    topic_matches += 0.5

            # Calculate topic score (0-1)
            if topic_words:
                topic_score = min(topic_matches / len(topic_words), 1.0)
                score += topic_score
                total_checks += 1

        # Average across all topics
        if total_checks > 0:
            score = score / total_checks

        # Boost for title matches
        title_lower = article.title.lower()
        for topic in topics:
            if topic.lower() in title_lower:
                score = min(score + 0.2, 1.0)

        # Boost for recent articles (within 12 hours)
        try:
            # Make both datetimes timezone-aware for comparison
            now = datetime.now(UTC)
            published_at = article.published_at

            # If published_at is naive, assume UTC
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=UTC)

            time_diff = now - published_at
            if time_diff.total_seconds() < 43200:  # 12 hours
                score = min(score + 0.1, 1.0)
        except Exception as e:
            logger.debug(f"Error calculating time difference: {e}")
            # If datetime comparison fails, skip the recency boost

        return score

    def _has_good_content_quality(self, article: Article) -> bool:
        """Check if article has good content quality."""
        # Skip articles with very short titles
        if len(article.title.strip()) < 10:
            return False

        # Skip articles with very short descriptions
        if len(article.description.strip()) < 20:
            return False

        # Skip articles with suspicious patterns
        suspicious_patterns = [
            r"\[removed\]",
            r"\[deleted\]",
            r"sign up",
            r"subscribe now",
            r"paywall",
        ]

        full_text = f"{article.title} {article.description}".lower()
        return all(not re.search(pattern, full_text) for pattern in suspicious_patterns)

    def deduplicate_by_content(self, articles: list[Article]) -> list[Article]:
        """Advanced deduplication based on content similarity."""
        if len(articles) <= 1:
            return articles

        unique_articles = []

        for current_article in articles:
            is_duplicate = False

            for existing_article in unique_articles:
                # Check content similarity
                if self._are_similar_articles(current_article, existing_article):
                    # Keep the one with higher relevance score
                    if (
                        current_article.relevance_score
                        > existing_article.relevance_score
                    ):
                        unique_articles.remove(existing_article)
                        unique_articles.append(current_article)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(current_article)

        return unique_articles

    def _are_similar_articles(self, article1: Article, article2: Article) -> bool:
        """Check if two articles are similar in content."""
        # Title similarity
        title_similarity = SequenceMatcher(
            None, article1.title.lower(), article2.title.lower()
        ).ratio()

        if title_similarity > 0.85:
            return True

        # Description similarity
        if article1.description and article2.description:
            desc_similarity = SequenceMatcher(
                None, article1.description.lower(), article2.description.lower()
            ).ratio()

            if desc_similarity > 0.80:
                return True

        # URL domain similarity (same story from different sources)
        return bool(self._same_story_different_source(article1.url, article2.url))

    def _same_story_different_source(self, url1: str, url2: str) -> bool:
        """Check if URLs might be the same story from different sources."""
        # Extract path components and look for similar patterns
        try:
            import urllib.parse as urlparse

            parsed1 = urlparse.urlparse(url1)
            parsed2 = urlparse.urlparse(url2)

            # Different domains but similar paths might indicate same story
            if parsed1.netloc != parsed2.netloc:
                path1_parts = [
                    part for part in parsed1.path.split("/") if len(part) > 3
                ]
                path2_parts = [
                    part for part in parsed2.path.split("/") if len(part) > 3
                ]

                # Check for common path elements
                common_parts = set(path1_parts) & set(path2_parts)
                if len(common_parts) >= 2:
                    return True

        except Exception:
            pass

        return False


class TopicMatcher:
    def __init__(self, topics: list[str]):
        self.topics = [topic.lower() for topic in topics]
        self.topic_keywords = self._expand_topics(topics)

    def _expand_topics(self, topics: list[str]) -> dict[str, list[str]]:
        """Expand topics with related keywords."""
        expanded = {}

        # Predefined keyword expansions
        expansions = {
            "artificial intelligence": [
                "ai",
                "machine learning",
                "deep learning",
                "neural network",
                "chatgpt",
                "gpt",
            ],
            "climate change": [
                "global warming",
                "carbon emission",
                "renewable energy",
                "sustainability",
                "carbon footprint",
            ],
            "technology": [
                "tech",
                "software",
                "hardware",
                "innovation",
                "digital",
                "computing",
            ],
            "space exploration": [
                "nasa",
                "spacex",
                "mars",
                "rocket",
                "satellite",
                "astronaut",
                "space station",
            ],
            "renewable energy": [
                "solar",
                "wind energy",
                "hydroelectric",
                "clean energy",
                "green energy",
                "sustainable",
            ],
        }

        for topic in topics:
            topic_lower = topic.lower()
            expanded[topic_lower] = [topic_lower]

            # Add predefined expansions
            if topic_lower in expansions:
                expanded[topic_lower].extend(expansions[topic_lower])

            # Add word variations
            words = topic_lower.split()
            for word in words:
                if len(word) > 3:  # Only expand meaningful words
                    expanded[topic_lower].append(word)

        return expanded

    def get_matching_topics(self, article: Article) -> list[str]:
        """Get topics that match the article."""
        matching_topics = []
        text = f"{article.title} {article.description} {article.content}".lower()

        for original_topic in self.topics:
            keywords = self.topic_keywords.get(original_topic, [original_topic])

            for keyword in keywords:
                if keyword in text:
                    matching_topics.append(original_topic)
                    break

        return matching_topics
