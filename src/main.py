#!/usr/bin/env python3
"""
Personal News - AI-powered daily news digest

This script fetches news articles based on your interests, generates AI summaries,
and sends a personalized newsletter to your email daily.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scheduler import NewsScheduler
from config.manager import ConfigManager

def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "personal_news.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def print_banner():
    """Print application banner."""
    banner = """
    ╔═══════════════════════════════════════════╗
    ║            Personal News Digest           ║
    ║         AI-powered daily newsletter       ║
    ╚═══════════════════════════════════════════╝
    """
    print(banner)

async def run_once(config_path: str = None, verbose: bool = False):
    """Run the news digest generation once."""
    setup_logging(verbose)
    print_banner()
    
    try:
        scheduler = NewsScheduler(config_path)
        await scheduler.run_once()
        print("✓ News digest generated and sent successfully!")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

async def test_config(config_path: str = None, verbose: bool = False):
    """Test the configuration by sending a test email."""
    setup_logging(verbose)
    print_banner()
    print("Testing email configuration...")
    
    try:
        scheduler = NewsScheduler(config_path)
        success = await scheduler.test_email_config()
        
        if success:
            print("✓ Email configuration is working correctly!")
        else:
            print("✗ Email configuration test failed")
            print("Please check your config/preferences.json file")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        sys.exit(1)

async def start_scheduler(config_path: str = None, verbose: bool = False):
    """Start the daily scheduler."""
    setup_logging(verbose)
    print_banner()
    print("Starting daily news scheduler...")
    
    try:
        scheduler = NewsScheduler(config_path)
        
        # Show status
        status = scheduler.get_status()
        print(f"Scheduler running: {status['running']}")
        
        # Run forever
        await scheduler.run_forever()
        
    except KeyboardInterrupt:
        print("\n✓ Scheduler stopped by user")
    except Exception as e:
        print(f"✗ Scheduler error: {e}")
        sys.exit(1)

def setup_config():
    """Interactive configuration setup."""
    print_banner()
    print("Setting up Personal News configuration...")
    
    config_path = Path(__file__).parent.parent / "config" / "preferences.json"
    
    if config_path.exists():
        response = input(f"Configuration already exists at {config_path}. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Configuration setup cancelled.")
            return
    
    print("\nPlease provide the following information:")
    
    # User information
    user_email = input("Your email address: ").strip()
    user_name = input("Your name (optional): ").strip() or "User"
    
    # Topics
    print("\nEnter topics you're interested in (comma-separated):")
    print("Examples: artificial intelligence, climate change, technology, space exploration")
    topics_input = input("Topics: ").strip()
    topics = [topic.strip() for topic in topics_input.split(",") if topic.strip()]
    
    # Email configuration
    print("\nEmail configuration:")
    sender_email = input("Sender email (Gmail recommended): ").strip()
    print("For Gmail, use an App Password (not your regular password)")
    print("See: https://support.google.com/accounts/answer/185833")
    sender_password = input("Email app password: ").strip()
    
    # Schedule
    schedule_time = input("Daily send time (HH:MM, 24-hour format, default 08:00): ").strip() or "08:00"
    
    # API Keys
    print("\nAI API Keys (at least one required):")
    newsapi_key = input("NewsAPI key (get from https://newsapi.org/): ").strip()
    openai_key = input("OpenAI API key (optional): ").strip()
    anthropic_key = input("Anthropic API key (optional): ").strip()
    
    if not openai_key and not anthropic_key:
        print("Warning: No AI API keys provided. Summaries will be basic.")
    
    # Create configuration
    config = {
        "user": {
            "email": user_email,
            "name": user_name,
            "timezone": "UTC"
        },
        "topics": topics,
        "sources": [
            "bbc-news",
            "reuters",
            "the-guardian",
            "techcrunch",
            "ars-technica"
        ],
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
    
    # Save configuration
    import json
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"\n✓ Configuration saved to {config_path}")
    print("\nNext steps:")
    print("1. Test your configuration: python -m src.main test")
    print("2. Run once: python -m src.main run")
    print("3. Start scheduler: python -m src.main start")

def show_status(config_path: str = None):
    """Show scheduler status."""
    try:
        scheduler = NewsScheduler(config_path)
        status = scheduler.get_status()
        
        print("Personal News Status")
        print("=" * 20)
        print(f"Scheduler running: {status['running']}")
        print(f"Jobs configured: {len(status['jobs'])}")
        
        for job in status['jobs']:
            print(f"  - {job['name']} (ID: {job['id']})")
            if job['next_run_time']:
                print(f"    Next run: {job['next_run_time']}")
            print(f"    Trigger: {job['trigger']}")
        
    except Exception as e:
        print(f"Error getting status: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Personal News - AI-powered daily digest")
    
    parser.add_argument(
        "command", 
        choices=["setup", "test", "run", "start", "status"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_config()
    elif args.command == "test":
        asyncio.run(test_config(args.config, args.verbose))
    elif args.command == "run":
        asyncio.run(run_once(args.config, args.verbose))
    elif args.command == "start":
        asyncio.run(start_scheduler(args.config, args.verbose))
    elif args.command == "status":
        show_status(args.config)

if __name__ == "__main__":
    main()