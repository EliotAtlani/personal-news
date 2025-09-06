import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SecretsManager:
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("secretsmanager", region_name=region_name)
        
    def get_secret(self, secret_name: str) -> dict:
        """Retrieve secrets from AWS Secrets Manager."""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_string = response["SecretString"]
            return json.loads(secret_string)
        except ClientError as e:
            logger.error(f"Error retrieving secret {secret_name}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing secret {secret_name} as JSON: {e}")
            raise
    
    def get_api_keys(self) -> dict:
        """Get API keys from the personal-news/api-keys secret."""
        return self.get_secret("personal-news/api-keys")