import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .s3_storage import S3PreferencesManager
from .secrets import SecretsManager

load_dotenv()


class UserConfig(BaseModel):
    email: str
    name: str = "User"
    timezone: str = "UTC"


class ScheduleConfig(BaseModel):
    day_of_week: int  # 1=Monday, 2=Tuesday, ..., 7=Sunday
    time: str = "12:00"


class ContentConfig(BaseModel):
    time_range: str = "last_week"
    max_articles: int = 5
    min_articles: int = 2
    summary_length: str = "medium"
    min_relevance_score: float = 0.5


class ProfileConfig(BaseModel):
    name: str
    subject_prefix: str
    schedule: ScheduleConfig
    topics: list = Field(default_factory=list)
    sources: list = Field(default_factory=list)
    content: ContentConfig = Field(default_factory=ContentConfig)


class EmailConfig(BaseModel):
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str
    sender_password: str


class APIKeys(BaseModel):
    newsapi: str = ""
    guardian: str = ""
    eventregistry: str = ""
    openai: str = ""
    anthropic: str = ""
    gemini: str = ""


class HistoryConfig(BaseModel):
    sent_articles: list = Field(default_factory=list)


class Config(BaseModel):
    user: UserConfig
    profiles: dict
    email: EmailConfig
    api_keys: APIKeys
    history: HistoryConfig = Field(default_factory=HistoryConfig)


class ProfileBasedConfig(BaseModel):
    """Configuration for a specific profile with shared settings"""

    user: UserConfig
    name: str
    subject_prefix: str
    topics: list
    sources: list
    schedule: ScheduleConfig
    content: ContentConfig
    email: EmailConfig
    api_keys: APIKeys
    history: HistoryConfig


class ConfigManager:
    def __init__(self, config_path: str | None = None, use_s3: bool | None = None):
        """
        Initialize ConfigManager with support for both local and S3 storage.

        Args:
            config_path: Local path for preferences (fallback or development)
            use_s3: Whether to use S3 storage. If None, determined by AWS_USE_S3 env var
        """
        # Determine storage method
        self.use_s3 = (
            use_s3
            if use_s3 is not None
            else os.getenv("AWS_USE_S3", "false").lower() == "true"
        )

        if self.use_s3:
            try:
                self.s3_manager = S3PreferencesManager()
            except Exception as e:
                # Fallback to local storage if S3 fails
                print(f"S3 initialization failed, falling back to local storage: {e}")
                self.use_s3 = False

        if not self.use_s3:
            if config_path is None:
                self.config_path = (
                    Path(__file__).parent.parent.parent / "config" / "preferences.json"
                )
            else:
                self.config_path = Path(config_path)

        self.config = self._load_config()

    def _load_config(self) -> Config:
        """Load configuration from S3 or local file, then override with Secrets Manager and environment variables."""
        try:
            if self.use_s3:
                config_data = self.s3_manager.load_preferences()
            else:
                with open(self.config_path) as f:
                    config_data = json.load(f)

            # Override with AWS Secrets Manager if available (production)
            if self.use_s3:  # Only use Secrets Manager in production
                try:
                    secrets_manager = SecretsManager()
                    api_keys = secrets_manager.get_api_keys()

                    for key, value in api_keys.items():
                        if key in [
                            "GUARDIAN_API_KEY",
                            "GEMINI_API_KEY",
                            "NEWSAPI_KEY",
                            "OPENAI_API_KEY",
                            "ANTHROPIC_API_KEY",
                        ]:
                            # Map environment variable names to config keys
                            config_key = key.lower().replace("_api_key", "")
                            if config_key == "newsapi":
                                config_key = "newsapi"
                            config_data["api_keys"][config_key] = value

                except Exception as e:
                    print(f"WARNING: Could not load from Secrets Manager: {e}")
                    print("Falling back to environment variables...")

            # Override with environment variables if they exist (local development)
            if os.getenv("NEWSAPI_KEY"):
                config_data["api_keys"]["newsapi"] = os.getenv("NEWSAPI_KEY")
            if os.getenv("GUARDIAN_API_KEY"):
                config_data["api_keys"]["guardian"] = os.getenv("GUARDIAN_API_KEY")
            if os.getenv("EVENTREGISTRY_API_KEY"):
                config_data["api_keys"]["eventregistry"] = os.getenv(
                    "EVENTREGISTRY_API_KEY"
                )
            if os.getenv("OPENAI_API_KEY"):
                config_data["api_keys"]["openai"] = os.getenv("OPENAI_API_KEY")
            if os.getenv("ANTHROPIC_API_KEY"):
                config_data["api_keys"]["anthropic"] = os.getenv("ANTHROPIC_API_KEY")
            if os.getenv("GEMINI_API_KEY"):
                config_data["api_keys"]["gemini"] = os.getenv("GEMINI_API_KEY")
            if os.getenv("EMAIL_PASSWORD"):
                config_data["email"]["sender_password"] = os.getenv("EMAIL_PASSWORD")

            return Config(**config_data)
        except Exception as e:
            raise Exception(f"Failed to load configuration: {e}")

    def save_config(self):
        """Save current configuration to S3 or local file."""
        config_data = self.config.model_dump()

        if self.use_s3:
            success = self.s3_manager.save_preferences(config_data)
            if not success:
                raise Exception("Failed to save configuration to S3")
        else:
            with open(self.config_path, "w") as f:
                json.dump(config_data, f, indent=4)

    def add_topic(self, topic: str):
        """Add a new topic to track."""
        if topic not in self.config.topics:
            self.config.topics.append(topic)
            self.save_config()

    def remove_topic(self, topic: str):
        """Remove a topic from tracking."""
        if topic in self.config.topics:
            self.config.topics.remove(topic)
            self.save_config()

    def update_schedule(self, time: str | None = None, enabled: bool | None = None):
        """Update schedule settings."""
        if time:
            self.config.schedule.time = time
        if enabled is not None:
            self.config.schedule.enabled = enabled
        self.save_config()

    def get_config(self, profile: str | None = None) -> ProfileBasedConfig:
        """Get configuration for a specific profile."""
        if profile is None:
            # Return first available profile if none specified
            profile = list(self.config.profiles.keys())[0]

        if profile not in self.config.profiles:
            raise ValueError(
                f"Profile '{profile}' not found. Available profiles: {list(self.config.profiles.keys())}"
            )

        profile_config = self.config.profiles[profile]

        # Handle both dict and ProfileConfig object cases
        if isinstance(profile_config, dict):
            return ProfileBasedConfig(
                user=self.config.user,
                name=profile_config["name"],
                subject_prefix=profile_config["subject_prefix"],
                topics=profile_config["topics"],
                sources=profile_config["sources"],
                schedule=profile_config["schedule"],
                content=profile_config["content"],
                email=self.config.email,
                api_keys=self.config.api_keys,
                history=self.config.history,
            )
        else:
            return ProfileBasedConfig(
                user=self.config.user,
                name=profile_config.name,
                subject_prefix=profile_config.subject_prefix,
                topics=profile_config.topics,
                sources=profile_config.sources,
                schedule=profile_config.schedule,
                content=profile_config.content,
                email=self.config.email,
                api_keys=self.config.api_keys,
                history=self.config.history,
            )

    def get_full_config(self) -> Config:
        """Get the full multi-profile configuration."""
        return self.config

    def add_sent_article(self, article_url: str):
        """Add article URL to history to prevent duplicates."""
        if article_url not in self.config.history.sent_articles:
            self.config.history.sent_articles.append(article_url)
            # Keep only last 1000 articles to prevent infinite growth
            if len(self.config.history.sent_articles) > 1000:
                self.config.history.sent_articles = self.config.history.sent_articles[
                    -1000:
                ]
            self.save_config()

    def is_article_sent(self, article_url: str) -> bool:
        """Check if article was already sent."""
        return article_url in self.config.history.sent_articles
