#!/usr/bin/env python3
"""
Simple runner for Personal News without complex imports
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Test basic imports
    print("Testing imports...")

    from src.config.manager import ConfigManager
    print("✓ Config manager imported successfully")

    # Test config loading
    try:
        config_manager = ConfigManager()
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"⚠ Configuration error (expected if not set up): {e}")

    print("\nPersonal News is ready!")
    print("Run setup with: python run.py setup")

except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Please check your dependencies and Python version")
    sys.exit(1)

if len(sys.argv) > 1 and sys.argv[1] == "setup":
    print("\n" + "="*50)
    print("PERSONAL NEWS SETUP")
    print("="*50)

    print("\nThis will create a configuration file for your daily news digest.")
    print("You'll need:")
    print("- NewsAPI key (free from newsapi.org)")
    print("- OpenAI or Anthropic API key")
    print("- Gmail app password")

    # Simple setup without complex scheduler
    config_path = project_root / "config" / "preferences.json"
    config_path.parent.mkdir(exist_ok=True)

    import json

    print(f"\nConfiguration will be saved to: {config_path}")

    if config_path.exists():
        response = input("Configuration exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            sys.exit(0)

    # Collect user input
    print("\n--- User Information ---")
    email = input("Your email address: ").strip()
    name = input("Your name (optional): ").strip() or "User"

    print("\n--- Topics of Interest ---")
    print("Enter topics separated by commas:")
    topics_input = input("Topics: ").strip()
    topics = [t.strip() for t in topics_input.split(",") if t.strip()]

    print("\n--- Email Configuration ---")
    sender_email = input("Gmail address for sending: ").strip()
    print("You need an App Password (not regular password)")
    print("Guide: https://support.google.com/accounts/answer/185833")
    sender_password = input("Gmail app password: ").strip()

    print("\n--- API Keys ---")
    newsapi_key = input("NewsAPI key: ").strip()
    openai_key = input("OpenAI API key (optional): ").strip()
    anthropic_key = input("Anthropic API key (optional): ").strip()

    schedule_time = input(
        "Daily send time (HH:MM, default 08:00): ").strip() or "08:00"

    # Create config
    config = {
        "user": {
            "email": email,
            "name": name,
            "timezone": "UTC"
        },
        "topics": topics,
        "sources": ["bbc-news", "reuters", "the-guardian", "techcrunch"],
        "schedule": {
            "time": schedule_time,
            "enabled": True
        },
        "content": {
            "max_articles": 10,
            "summary_length": "medium",
            "min_relevance_score": 0.6
        },
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": sender_email,
            "sender_password": sender_password
        },
        "api_keys": {
            "newsapi": newsapi_key,
            "openai": openai_key,
            "anthropic": anthropic_key
        }
    }

    # Save config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

    print(f"\n✓ Configuration saved!")
    print("\nNext steps:")
    print("1. Test with: python run.py test")
    print("2. Run once: python run.py run")

elif len(sys.argv) > 1 and sys.argv[1] == "test":
    print("\nTesting email configuration...")
    try:
        from src.config.manager import ConfigManager
        from src.email.sender import EmailSender

        config_manager = ConfigManager()
        config = config_manager.get_config()
        email_sender = EmailSender(config)

        success = email_sender.send_test_email()
        if success:
            print("✓ Test email sent successfully!")
        else:
            print("✗ Test email failed")

    except Exception as e:
        print(f"✗ Error: {e}")

elif len(sys.argv) > 1 and sys.argv[1] == "run":
    print("\nRunning news digest generation...")
    import asyncio

    async def run_digest():
        try:
            # Import here to avoid scheduler issues
            from src.config.manager import ConfigManager
            from src.news.fetchers import NewsFetcher
            from src.news.filters import ContentFilter
            from src.email.sender import EmailSender
            from datetime import datetime, timedelta

            config_manager = ConfigManager()
            config = config_manager.get_config()

            # Fetch news
            print("Fetching news...")
            news_fetcher = NewsFetcher(
                newsapi_key=getattr(config.api_keys, 'newsapi', None),
                guardian_key=getattr(config.api_keys, 'guardian', None),
                eventregistry_key=getattr(
                    config.api_keys, 'eventregistry', None)
            )

            articles = await news_fetcher.fetch_all_articles(
                topics=config.topics,
                sources=config.sources,
                from_date=datetime.now() - timedelta(days=1)
            )

            print(f"Found {len(articles)} articles")

            # Filter articles
            content_filter = ContentFilter(config.content.min_relevance_score)
            filtered_articles = content_filter.filter_articles(
                articles, config.topics)

            if config.content.max_articles:
                filtered_articles = filtered_articles[:config.content.max_articles]

            print(f"Filtered to {len(filtered_articles)} articles")

            if not filtered_articles:
                print("No relevant articles found")
                return

            # Generate AI summaries
            print("Generating summaries...")

            try:
                from src.ai.summarizer import NewsSummarizer

                summarizer = NewsSummarizer(
                    openai_key=getattr(config.api_keys, 'openai', None),
                    anthropic_key=getattr(config.api_keys, 'anthropic', None),
                    gemini_key=getattr(config.api_keys, 'gemini', None)
                )

                summaries = await summarizer.summarize_articles(
                    filtered_articles,
                    summary_length=config.content.summary_length
                )

                print(f"Generated {len(summaries)} AI summaries")

            except Exception as e:
                print(
                    f"AI summarization failed ({e}), using basic summaries...")

                # Fallback to basic summaries
                summaries = []
                from src.ai.summarizer import ArticleSummary

                for article in filtered_articles:
                    summary = ArticleSummary(
                        article=article,
                        brief_summary=article.description[:200] + "..." if len(
                            article.description) > 200 else article.description,
                        key_points=[
                            f"Source: {article.source}", f"Published: {article.published_at.strftime('%Y-%m-%d')}"],
                        category="General",
                        importance_score=article.relevance_score
                    )
                    summaries.append(summary)

            # Group by category
            try:
                categories = summarizer.group_summaries_by_category(summaries)
                print(f"Organized into {len(categories)} categories")
            except:
                # Fallback grouping
                categories = {"General": summaries}

            # Send email
            print("Sending newsletter...")
            email_sender = EmailSender(config)
            success = email_sender.send_newsletter(summaries, categories)

            if success:
                print("✓ Newsletter sent successfully!")
            else:
                print("✗ Failed to send newsletter")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(run_digest())

else:
    print("\nAvailable commands:")
    print("  setup - Interactive configuration setup")
    print("  test  - Test email configuration")
    print("  run   - Generate and send newsletter once")
