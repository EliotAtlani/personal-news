import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.ai.summarizer import NewsSummarizer
from src.config.manager import ConfigManager
from src.email.sender import EmailSender
from src.news.fetchers import NewsFetcher
from src.news.filters import ContentFilter

logger = logging.getLogger(__name__)


class NewsScheduler:
    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()

        # Initialize components
        self.news_fetcher = NewsFetcher(
            newsapi_key=self.config.api_keys.newsapi or None,
            guardian_key=self.config.api_keys.guardian or None,
            eventregistry_key=self.config.api_keys.eventregistry or None,
        )

        self.content_filter = ContentFilter(
            min_relevance_score=self.config.content.min_relevance_score
        )

        self.summarizer = NewsSummarizer(
            openai_key=self.config.api_keys.openai,
            anthropic_key=self.config.api_keys.anthropic,
            gemini_key=self.config.api_keys.gemini,
        )

        self.email_sender = EmailSender(self.config)

        # Set up scheduler
        self.scheduler = self._setup_scheduler()
        self._setup_signal_handlers()

    def _setup_scheduler(self) -> AsyncIOScheduler:
        """Set up the async scheduler with proper configuration."""
        jobstores = {"default": MemoryJobStore()}

        executors = {"default": AsyncIOExecutor()}

        job_defaults = {
            "coalesce": True,  # Combine multiple pending executions
            "max_instances": 1,  # Only one instance at a time
            "misfire_grace_time": 3600,  # 1 hour grace period
        }

        scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        return scheduler

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def generate_daily_digest(self):
        """Main function to generate and send the daily news digest."""
        logger.info("Starting daily news digest generation...")

        try:
            # Fetch news articles
            logger.info("Fetching news articles...")
            articles = await self.news_fetcher.fetch_all_articles(
                topics=self.config.topics,
                sources=self.config.sources,
                from_date=datetime.now() - timedelta(days=1),
            )

            logger.info(f"Fetched {len(articles)} articles")

            if not articles:
                logger.warning("No articles fetched, sending empty digest")
                await self._send_empty_digest()
                return

            # Filter and rank articles
            logger.info("Filtering and ranking articles...")
            filtered_articles = self.content_filter.filter_articles(
                articles, self.config.topics
            )

            # Check if we have minimum articles required
            min_articles = getattr(self.config.content, "min_articles", 1)
            if len(filtered_articles) < min_articles:
                logger.warning(
                    f"Only {len(filtered_articles)} articles found, but minimum {min_articles} required"
                )
                # Lower the relevance score threshold to get more articles
                self.content_filter.min_relevance_score = max(
                    0.3, self.content_filter.min_relevance_score - 0.2
                )
                filtered_articles = self.content_filter.filter_articles(
                    articles, self.config.topics
                )
                logger.info(
                    f"Lowered relevance threshold, now have {len(filtered_articles)} articles"
                )

            # Limit to max articles
            max_articles = self.config.content.max_articles
            if len(filtered_articles) > max_articles:
                filtered_articles = filtered_articles[:max_articles]

            logger.info(f"Final count: {len(filtered_articles)} articles")

            if not filtered_articles:
                logger.warning("No articles passed filtering, sending empty digest")
                await self._send_empty_digest()
                return

            # Generate summaries
            logger.info("Generating AI summaries...")
            summaries = await self.summarizer.summarize_articles(
                filtered_articles, summary_length=self.config.content.summary_length
            )

            logger.info(f"Generated {len(summaries)} summaries")

            # Group by category
            categories = self.summarizer.group_summaries_by_category(summaries)

            # Send newsletter
            logger.info("Sending newsletter...")
            success = self.email_sender.send_newsletter(summaries, categories)

            if success:
                logger.info("Daily digest sent successfully!")
                self._log_digest_stats(summaries, categories)
            else:
                logger.error("Failed to send daily digest")
                await self._send_error_notification("Failed to send newsletter")

        except Exception as e:
            logger.error(f"Error generating daily digest: {e}")
            await self._send_error_notification(str(e))

    async def _send_empty_digest(self):
        """Send an empty digest notification."""
        try:
            empty_summaries = []
            empty_categories = {}
            self.email_sender.send_newsletter(empty_summaries, empty_categories)
            logger.info("Empty digest notification sent")
        except Exception as e:
            logger.error(f"Failed to send empty digest: {e}")

    async def _send_error_notification(self, error_message: str):
        """Send error notification email."""
        try:
            self.email_sender.send_error_notification(error_message)
            logger.info("Error notification sent")
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")

    def _log_digest_stats(self, summaries, categories):
        """Log statistics about the generated digest."""
        logger.info("=== Daily Digest Statistics ===")
        logger.info(f"Total articles: {len(summaries)}")
        logger.info(f"Categories: {len(categories)}")

        for category, articles in categories.items():
            avg_importance = sum(s.importance_score for s in articles) / len(articles)
            logger.info(
                f"  {category}: {len(articles)} articles (avg importance: {avg_importance:.2f})"
            )

        if summaries:
            top_article = max(summaries, key=lambda s: s.importance_score)
            logger.info(
                f"Top article: '{top_article.article.title}' (score: {top_article.importance_score:.2f})"
            )

    def schedule_daily_digest(self):
        """Schedule the daily digest job."""
        if not self.config.schedule.enabled:
            logger.info("Daily scheduling is disabled in configuration")
            return

        # Parse time
        try:
            hour, minute = self.config.schedule.time.split(":")
            hour = int(hour)
            minute = int(minute)
        except ValueError:
            logger.error(f"Invalid schedule time format: {self.config.schedule.time}")
            hour, minute = 8, 0  # Default to 8:00 AM

        # Schedule the job
        self.scheduler.add_job(
            self.generate_daily_digest,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_digest",
            name="Daily News Digest",
            replace_existing=True,
        )

        logger.info(f"Daily digest scheduled for {hour:02d}:{minute:02d} UTC")

    def schedule_test_run(self, delay_minutes: int = 1):
        """Schedule a test run after a specified delay."""
        run_time = datetime.now() + timedelta(minutes=delay_minutes)

        self.scheduler.add_job(
            self.generate_daily_digest,
            trigger="date",
            run_date=run_time,
            id="test_digest",
            name="Test News Digest",
            replace_existing=True,
        )

        logger.info(
            f"Test digest scheduled for {run_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    async def run_once(self):
        """Run the digest generation once immediately."""
        logger.info("Running digest generation immediately...")
        await self.generate_daily_digest()

    async def test_email_config(self):
        """Test email configuration by sending a test email."""
        logger.info("Testing email configuration...")
        success = self.email_sender.send_test_email()

        if success:
            logger.info("Test email sent successfully!")
        else:
            logger.error("Failed to send test email - check your configuration")

        return success

    def start(self):
        """Start the scheduler."""
        logger.info("Starting news scheduler...")

        # Schedule the daily job
        self.schedule_daily_digest()

        # Start scheduler
        self.scheduler.start()
        logger.info("Scheduler started successfully")

        # Print next run time
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            logger.info(f"Next run: {job.next_run_time}")

    def stop(self):
        """Stop the scheduler gracefully."""
        logger.info("Stopping news scheduler...")

        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    async def run_forever(self):
        """Run the scheduler indefinitely."""
        self.start()

        try:
            # Keep the event loop running
            while True:
                await asyncio.sleep(3600)  # Check every hour

                # Reload configuration if needed
                if self._should_reload_config():
                    logger.info("Reloading configuration...")
                    self._reload_configuration()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Unexpected error in scheduler: {e}")
        finally:
            self.stop()

    def _should_reload_config(self) -> bool:
        """Check if configuration should be reloaded."""
        # For now, just return False. In the future, we could check
        # file modification times or add a reload signal
        return False

    def _reload_configuration(self):
        """Reload configuration and update components."""
        try:
            self.config_manager = ConfigManager()
            self.config = self.config_manager.get_config()

            # Update scheduler job
            self.schedule_daily_digest()

            logger.info("Configuration reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")

    def get_status(self) -> dict:
        """Get scheduler status information."""
        jobs = self.scheduler.get_jobs()

        status = {"running": self.scheduler.running, "jobs": []}

        for job in jobs:
            status["jobs"].append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                    "trigger": str(job.trigger),
                }
            )

        return status
