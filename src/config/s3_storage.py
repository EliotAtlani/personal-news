import json
import os
import boto3
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class S3PreferencesManager:
    def __init__(self, bucket_name: str = None, preferences_key: str = "preferences.json"):
        """
        Initialize S3 preferences manager.
        
        Args:
            bucket_name: S3 bucket name (defaults to env var S3_BUCKET_NAME)
            preferences_key: Key name for preferences file in S3
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        self.preferences_key = preferences_key
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name must be provided either as parameter or S3_BUCKET_NAME env var")
        
        try:
            # Initialize S3 client - will use AWS credentials from environment/IAM role
            self.s3_client = boto3.client('s3')
            logger.info(f"Initialized S3 client for bucket: {self.bucket_name}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure AWS credentials.")
    
    def load_preferences(self) -> Dict[str, Any]:
        """
        Load preferences from S3.
        
        Returns:
            Dict containing preferences data
            
        Raises:
            Exception if preferences cannot be loaded
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.preferences_key
            )
            preferences_data = json.loads(response['Body'].read().decode('utf-8'))
            logger.info("Successfully loaded preferences from S3")
            return preferences_data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning("Preferences file not found in S3, will create new one")
                return self._get_default_preferences()
            elif error_code == 'NoSuchBucket':
                raise Exception(f"S3 bucket '{self.bucket_name}' does not exist")
            else:
                raise Exception(f"Failed to load preferences from S3: {e}")
        except Exception as e:
            raise Exception(f"Failed to load preferences from S3: {e}")
    
    def save_preferences(self, preferences: Dict[str, Any]) -> bool:
        """
        Save preferences to S3.
        
        Args:
            preferences: Dict containing preferences data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            preferences_json = json.dumps(preferences, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.preferences_key,
                Body=preferences_json,
                ContentType='application/json'
            )
            
            logger.info("Successfully saved preferences to S3")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to save preferences to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to save preferences to S3: {e}")
            return False
    
    def backup_preferences(self, backup_suffix: str = None) -> bool:
        """
        Create a backup of current preferences in S3.
        
        Args:
            backup_suffix: Optional suffix for backup filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if backup_suffix is None:
                from datetime import datetime
                backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_key = f"backups/preferences_{backup_suffix}.json"
            
            # Copy current preferences to backup location
            self.s3_client.copy_object(
                CopySource={'Bucket': self.bucket_name, 'Key': self.preferences_key},
                Bucket=self.bucket_name,
                Key=backup_key
            )
            
            logger.info(f"Successfully created preferences backup: {backup_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create preferences backup: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create preferences backup: {e}")
            return False
    
    def preferences_exist(self) -> bool:
        """
        Check if preferences file exists in S3.
        
        Returns:
            True if preferences exist, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=self.preferences_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            raise
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """
        Return default preferences structure.
        
        Returns:
            Dict with default preferences
        """
        return {
            "user": {
                "email": "",
                "name": "User",
                "timezone": "UTC"
            },
            "topics": [],
            "sources": [],
            "schedule": {
                "time": "08:00",
                "enabled": True
            },
            "content": {
                "max_articles": 10,
                "min_articles": 1,
                "summary_length": "medium",
                "min_relevance_score": 0.6
            },
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": ""
            },
            "api_keys": {
                "newsapi": "",
                "guardian": "",
                "eventregistry": "",
                "openai": "",
                "anthropic": "",
                "gemini": ""
            }
        }