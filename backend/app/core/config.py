import os
import logging

logger = logging.getLogger(__name__)

class Settings:
    # Database configuration - prioritize DATABASE_URL from environment
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Storage configuration (R2 is required)
    R2_ENDPOINT: str = os.getenv("R2_ENDPOINT", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET: str = os.getenv("R2_BUCKET", "")

    # AWS credentials for AI services
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_TEMP_BUCKET: str = os.getenv("AWS_TEMP_BUCKET", "")
    
    def validate(self):
        # Required settings for all environments
        required_settings = [
            "DATABASE_URL", 
            "R2_ENDPOINT", 
            "R2_ACCESS_KEY_ID", 
            "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET"
        ]
        
        # Optional AWS settings - only required if using AWS AI services
        aws_settings = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY", 
            "AWS_TEMP_BUCKET"
        ]

        missing = []
        for setting in required_settings:
            value = getattr(self, setting, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing.append(setting)

        if missing:
            logger.error(f"Missing required config values: {missing}")
            raise RuntimeError(f"Missing required config values: {missing}")
            
        # Check AWS settings
        aws_missing = []
        for setting in aws_settings:
            value = getattr(self, setting, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                aws_missing.append(setting)
                
        if aws_missing:
            logger.warning(f"AWS settings missing: {aws_missing}. AWS AI services will be disabled.")

        # Validate R2 configuration
        if '<' in self.R2_ENDPOINT or 'your-r2' in self.R2_ENDPOINT:
            raise ValueError("R2_ENDPOINT contains placeholder values. Please set proper R2 configuration.")

        return True


settings = Settings()
try:
    settings.validate()
except Exception as e:
    logger.error(f"Settings validation failed: {e}")
