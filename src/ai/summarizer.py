import asyncio
import logging
from datetime import datetime

import anthropic
import google.generativeai as genai
import openai

from src.news.fetchers import Article

logger = logging.getLogger(__name__)


class ArticleSummary:
    def __init__(
        self,
        article: Article,
        brief_summary: str,
        key_points: list[str],
        category: str = "General",
        importance_score: float = 0.5,
    ):
        self.article = article
        self.brief_summary = brief_summary
        self.key_points = key_points
        self.category = category
        self.importance_score = importance_score
        self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "article": self.article.to_dict(),
            "brief_summary": self.brief_summary,
            "key_points": self.key_points,
            "category": self.category,
            "importance_score": self.importance_score,
            "created_at": self.created_at.isoformat(),
        }


class OpenAISummarizer:
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    async def summarize_article(
        self, article: Article, summary_length: str = "medium"
    ) -> ArticleSummary:
        """Summarize a single article using OpenAI."""
        try:
            # Prepare content for summarization
            content = f"Title: {article.title}\n"
            content += f"Description: {article.description}\n"
            if article.content:
                content += (
                    f"Content: {article.content[:2000]}\n"  # Limit content length
                )
            content += f"Source: {article.source}"

            # Determine summary length
            length_map = {
                "short": "1-2 sentences",
                "medium": "2-3 sentences",
                "long": "3-4 sentences",
            }
            target_length = length_map.get(summary_length, "2-3 sentences")

            # Create summarization prompt
            prompt = f"""
            Please analyze this news article and provide:
            1. A brief summary in {target_length}
            2. 3-5 key points as bullet points
            3. A category (Technology, Politics, Science, Business, Health, Sports, Entertainment, or General)
            4. An importance score from 0.0 to 1.0 (0.0 = not important, 1.0 = extremely important)
            
            Article:
            {content}
            
            Please format your response as:
            SUMMARY: [brief summary]
            KEY_POINTS: [bullet points]
            CATEGORY: [category]
            IMPORTANCE: [score]
            """

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional news summarizer. Provide concise, accurate summaries and analysis.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.3,
            )

            return self._parse_openai_response(
                article, response.choices[0].message.content
            )

        except Exception as e:
            logger.error(f"Error summarizing article with OpenAI: {e}")
            return self._fallback_summary(article)

    def _parse_openai_response(
        self, article: Article, response_text: str
    ) -> ArticleSummary:
        """Parse OpenAI response into ArticleSummary object."""
        try:
            lines = response_text.strip().split("\n")

            summary = ""
            key_points = []
            category = "General"
            importance_score = 0.5

            current_section = None

            for line in lines:
                line = line.strip()
                if line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                    current_section = "summary"
                elif line.startswith("KEY_POINTS:"):
                    current_section = "key_points"
                    points_text = line.replace("KEY_POINTS:", "").strip()
                    if points_text:
                        key_points.append(points_text)
                elif line.startswith("CATEGORY:"):
                    category = line.replace("CATEGORY:", "").strip()
                elif line.startswith("IMPORTANCE:"):
                    try:
                        importance_score = float(
                            line.replace("IMPORTANCE:", "").strip()
                        )
                    except ValueError:
                        importance_score = 0.5
                elif (
                    line.startswith(("•", "-", "*"))
                ):
                    if current_section == "key_points":
                        key_points.append(line.lstrip("•-* ").strip())
                elif current_section == "key_points" and line:
                    key_points.append(line)

            # Ensure we have at least some content
            if not summary:
                summary = (
                    article.description[:200] + "..."
                    if len(article.description) > 200
                    else article.description
                )

            if not key_points:
                key_points = [
                    f"Source: {article.source}",
                    f"Published: {article.published_at.strftime('%Y-%m-%d')}",
                ]

            return ArticleSummary(
                article, summary, key_points, category, importance_score
            )

        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            return self._fallback_summary(article)


class AnthropicSummarizer:
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def summarize_article(
        self, article: Article, summary_length: str = "medium"
    ) -> ArticleSummary:
        """Summarize a single article using Anthropic Claude."""
        try:
            # Prepare content for summarization
            content = f"Title: {article.title}\n"
            content += f"Description: {article.description}\n"
            if article.content:
                content += f"Content: {article.content[:2000]}\n"
            content += f"Source: {article.source}"

            # Determine summary length
            length_map = {
                "short": "1-2 sentences",
                "medium": "2-3 sentences",
                "long": "3-4 sentences",
            }
            target_length = length_map.get(summary_length, "2-3 sentences")

            prompt = f"""
            Please analyze this news article and provide:
            1. A brief summary in {target_length}
            2. 3-5 key points as bullet points
            3. A category (Technology, Politics, Science, Business, Health, Sports, Entertainment, or General)
            4. An importance score from 0.0 to 1.0
            
            Article:
            {content}
            
            Format as:
            SUMMARY: [summary]
            KEY_POINTS:
            • [point 1]
            • [point 2]
            • [point 3]
            CATEGORY: [category]
            IMPORTANCE: [score]
            """

            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            return self._parse_anthropic_response(article, response.content[0].text)

        except Exception as e:
            logger.error(f"Error summarizing article with Anthropic: {e}")
            return self._fallback_summary(article)

    def _parse_anthropic_response(
        self, article: Article, response_text: str
    ) -> ArticleSummary:
        """Parse Anthropic response into ArticleSummary object."""
        # Similar parsing logic to OpenAI
        return self._parse_openai_response(article, response_text)


class GeminiSummarizer:
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    async def summarize_article(
        self, article: Article, summary_length: str = "medium"
    ) -> ArticleSummary:
        """Summarize a single article using Google Gemini."""
        try:
            # Prepare content for summarization
            content = f"Title: {article.title}\n"
            content += f"Description: {article.description}\n"
            if article.content:
                content += f"Content: {article.content[:2000]}\n"
            content += f"Source: {article.source}"

            # Determine summary length
            length_map = {
                "short": "1-2 sentences",
                "medium": "2-3 sentences",
                "long": "3-4 sentences",
            }
            target_length = length_map.get(summary_length, "2-3 sentences")

            # Create summarization prompt
            prompt = f"""
            Please analyze this news article and provide:
            1. A brief summary in {target_length}
            2. 3-5 key points as bullet points
            3. A category (Technology, Politics, Science, Business, Health, Sports, Entertainment, or General)
            4. An importance score from 0.0 to 1.0 (0.0 = not important, 1.0 = extremely important)
            
            Article:
            {content}
            
            Please format your response exactly as:
            SUMMARY: [brief summary]
            KEY_POINTS:
            • [point 1]
            • [point 2]
            • [point 3]
            CATEGORY: [category]
            IMPORTANCE: [score]
            """

            response = await asyncio.to_thread(self.model.generate_content, prompt)

            return self._parse_gemini_response(article, response.text)

        except Exception as e:
            logger.error(f"Error summarizing article with Gemini: {e}")
            return self._fallback_summary(article)

    def _parse_gemini_response(
        self, article: Article, response_text: str
    ) -> ArticleSummary:
        """Parse Gemini response into ArticleSummary object."""
        try:
            lines = response_text.strip().split("\n")

            summary = ""
            key_points = []
            category = "General"
            importance_score = 0.5

            current_section = None

            for line in lines:
                line = line.strip()
                if line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                    current_section = "summary"
                elif line.startswith("KEY_POINTS:"):
                    current_section = "key_points"
                    points_text = line.replace("KEY_POINTS:", "").strip()
                    if points_text:
                        key_points.append(points_text)
                elif line.startswith("CATEGORY:"):
                    category = line.replace("CATEGORY:", "").strip()
                elif line.startswith("IMPORTANCE:"):
                    try:
                        importance_score = float(
                            line.replace("IMPORTANCE:", "").strip()
                        )
                        # Clamp to 0.0-1.0 range
                        importance_score = max(0.0, min(1.0, importance_score))
                    except ValueError:
                        importance_score = 0.5
                elif (
                    line.startswith(("•", "-", "*"))
                ):
                    if current_section == "key_points" or not current_section:
                        key_points.append(line.lstrip("•-* ").strip())
                elif (
                    current_section == "key_points"
                    and line
                    and not line.startswith(("CATEGORY:", "IMPORTANCE:"))
                ):
                    key_points.append(line)

            # Ensure we have at least some content
            if not summary:
                summary = (
                    article.description[:200] + "..."
                    if len(article.description) > 200
                    else article.description
                )

            if not key_points:
                key_points = [
                    f"Source: {article.source}",
                    f"Published: {article.published_at.strftime('%Y-%m-%d')}",
                ]

            return ArticleSummary(
                article, summary, key_points, category, importance_score
            )

        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return self._fallback_summary(article)

    def _fallback_summary(self, article: Article) -> ArticleSummary:
        """Create a basic summary when AI summarization fails."""
        summary = (
            article.description[:200] + "..."
            if len(article.description) > 200
            else article.description
        )

        key_points = [
            f"Source: {article.source}",
            f"Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}",
            "Full article available at source link",
        ]

        # Basic categorization based on keywords
        category = self._simple_categorize(article)

        return ArticleSummary(
            article=article,
            brief_summary=summary,
            key_points=key_points,
            category=category,
            importance_score=article.relevance_score,
        )

    def _simple_categorize(self, article: Article) -> str:
        """Simple rule-based categorization."""
        text = f"{article.title} {article.description}".lower()

        categories = {
            "Technology": [
                "tech",
                "ai",
                "software",
                "digital",
                "computer",
                "internet",
                "app",
            ],
            "Science": [
                "research",
                "study",
                "scientist",
                "discovery",
                "climate",
                "space",
            ],
            "Business": [
                "company",
                "business",
                "market",
                "economy",
                "financial",
                "stock",
            ],
            "Health": [
                "health",
                "medical",
                "hospital",
                "disease",
                "treatment",
                "vaccine",
            ],
            "Politics": [
                "government",
                "political",
                "election",
                "president",
                "congress",
                "policy",
            ],
            "Sports": ["sport", "game", "team", "player", "championship", "olympic"],
        }

        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category

        return "General"


class NewsSummarizer:
    def __init__(
        self, openai_key: str = None, anthropic_key: str = None, gemini_key: str = None
    ):
        self.openai_summarizer = OpenAISummarizer(openai_key) if openai_key else None
        self.anthropic_summarizer = (
            AnthropicSummarizer(anthropic_key) if anthropic_key else None
        )
        self.gemini_summarizer = GeminiSummarizer(gemini_key) if gemini_key else None

        if (
            not self.openai_summarizer
            and not self.anthropic_summarizer
            and not self.gemini_summarizer
        ):
            raise ValueError(
                "At least one AI service (OpenAI, Anthropic, or Gemini) API key must be provided"
            )

    async def summarize_articles(
        self,
        articles: list[Article],
        summary_length: str = "medium",
        max_concurrent: int = 5,
    ) -> list[ArticleSummary]:
        """Summarize multiple articles concurrently."""
        if not articles:
            return []

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def summarize_single(article: Article) -> ArticleSummary:
            async with semaphore:
                # Try Gemini first (most cost-effective and fast)
                if self.gemini_summarizer:
                    try:
                        return await self.gemini_summarizer.summarize_article(
                            article, summary_length
                        )
                    except Exception as e:
                        logger.warning(
                            f"Gemini summarization failed, trying OpenAI: {e}"
                        )

                # Fallback to OpenAI
                if self.openai_summarizer:
                    try:
                        return await self.openai_summarizer.summarize_article(
                            article, summary_length
                        )
                    except Exception as e:
                        logger.warning(
                            f"OpenAI summarization failed, trying Anthropic: {e}"
                        )

                # Fallback to Anthropic
                if self.anthropic_summarizer:
                    try:
                        return await self.anthropic_summarizer.summarize_article(
                            article, summary_length
                        )
                    except Exception as e:
                        logger.error(f"Anthropic summarization also failed: {e}")

                # Final fallback
                return self._fallback_summary(article)

        # Process articles concurrently
        tasks = [summarize_single(article) for article in articles]
        summaries = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return valid summaries
        valid_summaries = []
        for summary in summaries:
            if isinstance(summary, ArticleSummary):
                valid_summaries.append(summary)
            elif isinstance(summary, Exception):
                logger.error(f"Summarization task failed: {summary}")

        # Sort by importance score
        valid_summaries.sort(key=lambda x: x.importance_score, reverse=True)

        return valid_summaries

    def _fallback_summary(self, article: Article) -> ArticleSummary:
        """Create a basic summary when AI summarization fails."""
        # Basic summary using the description
        summary = (
            article.description[:200] + "..."
            if len(article.description) > 200
            else article.description
        )

        # Basic key points
        key_points = [
            f"Source: {article.source}",
            f"Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}",
            "Full article available at source link",
        ]

        # Basic categorization based on keywords
        category = self._simple_categorize(article)

        return ArticleSummary(
            article=article,
            brief_summary=summary,
            key_points=key_points,
            category=category,
            importance_score=article.relevance_score,
        )

    def _simple_categorize(self, article: Article) -> str:
        """Simple rule-based categorization."""
        text = f"{article.title} {article.description}".lower()

        categories = {
            "Technology": [
                "tech",
                "ai",
                "software",
                "digital",
                "computer",
                "internet",
                "app",
            ],
            "Science": [
                "research",
                "study",
                "scientist",
                "discovery",
                "climate",
                "space",
            ],
            "Business": [
                "company",
                "business",
                "market",
                "economy",
                "financial",
                "stock",
            ],
            "Health": [
                "health",
                "medical",
                "hospital",
                "disease",
                "treatment",
                "vaccine",
            ],
            "Politics": [
                "government",
                "political",
                "election",
                "president",
                "congress",
                "policy",
            ],
            "Sports": ["sport", "game", "team", "player", "championship", "olympic"],
        }

        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category

        return "General"

    def group_summaries_by_category(
        self, summaries: list[ArticleSummary]
    ) -> dict[str, list[ArticleSummary]]:
        """Group summaries by category for better organization."""
        grouped = {}
        for summary in summaries:
            category = summary.category
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(summary)

        # Sort within each category by importance
        for category in grouped:
            grouped[category].sort(key=lambda x: x.importance_score, reverse=True)

        return grouped
