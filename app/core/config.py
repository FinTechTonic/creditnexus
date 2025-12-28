"""Configuration management using pydantic-settings for type-safe environment variables."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    This class provides a typed interface to environment variables,
    ensuring that required configuration (like API keys) is present
    at startup time. If a required key is missing, the application
    will fail fast rather than failing halfway through a transaction.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    OPENAI_API_KEY: SecretStr
    
    # Sentinel Hub credentials for satellite imagery
    SENTINELHUB_KEY: SecretStr = None
    SENTINELHUB_SECRET: SecretStr = None
    
    def get_secret_value(self, key: str) -> str:
        """Get the secret value for a given key."""
        if key == "OPENAI_API_KEY":
            return self.OPENAI_API_KEY.get_secret_value()
        raise ValueError(f"Unknown secret key: {key}")


# Global settings object
settings = Settings()

