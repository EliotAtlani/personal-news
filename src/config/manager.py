import json
import os
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from .s3_storage import S3PreferencesManager

load_dotenv()

class UserConfig(BaseModel):
    email: str
    name: str = "User"
    timezone: str = "UTC"

class ScheduleConfig(BaseModel):
    time: str = "08:00"
    enabled: bool = True

class ContentConfig(BaseModel):
    max_articles: int = 10
    min_articles: int = 1
    summary_length: str = "medium"
    min_relevance_score: float = 0.6

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

class Config(BaseModel):
    user: UserConfig
    topics: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    content: ContentConfig = Field(default_factory=ContentConfig)
    email: EmailConfig
    api_keys: APIKeys

class ConfigManager:
    def __init__(self, config_path: str = None, use_s3: bool = None):
        """
        Initialize ConfigManager with support for both local and S3 storage.
        
        Args:
            config_path: Local path for preferences (fallback or development)
            use_s3: Whether to use S3 storage. If None, determined by AWS_USE_S3 env var
        """
        # Determine storage method
        self.use_s3 = use_s3 if use_s3 is not None else os.getenv('AWS_USE_S3', 'false').lower() == 'true'
        
        if self.use_s3:
            try:
                self.s3_manager = S3PreferencesManager()
            except Exception as e:
                # Fallback to local storage if S3 fails
                print(f"S3 initialization failed, falling back to local storage: {e}")
                self.use_s3 = False
        
        if not self.use_s3:
            if config_path is None:
                self.config_path = Path(__file__).parent.parent.parent / "config" / "preferences.json"
            else:
                self.config_path = Path(config_path)
        
        self.config = self._load_config()
    
    def _load_config(self) -> Config:
        """Load configuration from S3 or local file and environment variables."""
        try:
            if self.use_s3:
                config_data = self.s3_manager.load_preferences()
            else:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
            
            # Override with environment variables if they exist
            if os.getenv('NEWSAPI_KEY'):
                config_data['api_keys']['newsapi'] = os.getenv('NEWSAPI_KEY')
            if os.getenv('GUARDIAN_API_KEY'):
                config_data['api_keys']['guardian'] = os.getenv('GUARDIAN_API_KEY')
            if os.getenv('EVENTREGISTRY_API_KEY'):
                config_data['api_keys']['eventregistry'] = os.getenv('EVENTREGISTRY_API_KEY')
            if os.getenv('OPENAI_API_KEY'):
                config_data['api_keys']['openai'] = os.getenv('OPENAI_API_KEY')
            if os.getenv('ANTHROPIC_API_KEY'):
                config_data['api_keys']['anthropic'] = os.getenv('ANTHROPIC_API_KEY')
            if os.getenv('GEMINI_API_KEY'):
                config_data['api_keys']['gemini'] = os.getenv('GEMINI_API_KEY')
            if os.getenv('EMAIL_PASSWORD'):
                config_data['email']['sender_password'] = os.getenv('EMAIL_PASSWORD')
            
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
            with open(self.config_path, 'w') as f:
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
    
    def update_schedule(self, time: str = None, enabled: bool = None):
        """Update schedule settings."""
        if time:
            self.config.schedule.time = time
        if enabled is not None:
            self.config.schedule.enabled = enabled
        self.save_config()
    
    def get_config(self) -> Config:
        """Get current configuration."""
        return self.config