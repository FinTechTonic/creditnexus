"""Configuration management using pydantic-settings for type-safe environment variables."""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Optional, List
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    VLLM = "vllm"
    HUGGINGFACE = "huggingface"


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
    
    # Existing OpenAI settings
    OPENAI_API_KEY: SecretStr
    
    # Sentinel Hub credentials for satellite imagery
    SENTINELHUB_KEY: Optional[SecretStr] = None
    SENTINELHUB_SECRET: Optional[SecretStr] = None
    
    # LLM Provider Configuration
    LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI
    LLM_MODEL: str = "gpt-4o"  # Default model name
    # For HuggingFace, you can specify the provider in two ways:
    # 1. In the model name: "model:provider" (e.g., "deepseek-ai/DeepSeek-V3.2-Exp:novita")
    #    - Provider in model name takes highest priority
    # 2. Via HUGGINGFACE_INFERENCE_PROVIDER env var (e.g., "novita")
    #    - Used if no provider in model name
    # Recommended models for Novita:
    # - "meta-llama/Llama-3.1-8B-Instruct" or "meta-llama/Llama-3.1-8B-Instruct:novita"
    # - "microsoft/Phi-3.5-mini-instruct" or "microsoft/Phi-3.5-mini-instruct:novita"
    # - "deepseek-ai/DeepSeek-V3.2-Exp:novita" (example from user config)
    LLM_TEMPERATURE: float = 0.0
    
    # vLLM-specific settings
    VLLM_BASE_URL: Optional[str] = None  # e.g., "http://localhost:8000"
    VLLM_API_KEY: Optional[SecretStr] = None  # Optional, for auth
    
    # HuggingFace-specific settings
    HUGGINGFACE_API_KEY: Optional[SecretStr] = None
    HUGGINGFACE_BASE_URL: Optional[str] = None  # Defaults to https://api-inference.huggingface.co/v1
    # For HuggingFace Inference Providers (Cohere, fal, etc.):
    # Use HUGGINGFACE_BASE_URL=router.huggingface.co/{provider}/v3/openai
    # Or use init_chat_model with model_provider="huggingface" and provider parameter
    HUGGINGFACE_INFERENCE_PROVIDER: Optional[str] = "novita"  # Default: "novita" (preferred provider)
    # Available providers: black-forest-labs, cerebras, cohere, fal-ai, featherless-ai, 
    # fireworks-ai, groq, hf-inference, hyperbolic, nebius, novita, nscale, openai, 
    # replicate, sambanova, together
    # "auto" selects first available provider based on user preferences at hf.co/settings/inference-providers
    # Novita supports models like Llama-3.1-8B-Instruct, Phi-3.5-mini-instruct, and others
    
    # HuggingFace Local Model Configuration (separate from inference endpoints)
    # Set to True to load models locally using transformers (requires GPU/CPU resources)
    # Set to False to use inference endpoints (API-based, no local resources needed)
    HUGGINGFACE_USE_LOCAL: bool = False  # Use local models instead of inference endpoints
    # When HUGGINGFACE_USE_LOCAL=True:
    # - Models are loaded locally using transformers library
    # - Requires sufficient RAM/VRAM for the model
    # - No API calls, works offline
    # - HUGGINGFACE_INFERENCE_PROVIDER is ignored
    # When HUGGINGFACE_USE_LOCAL=False (default):
    # - Uses inference endpoints (Novita, Together, etc.)
    # - Requires HUGGINGFACE_API_KEY
    # - Uses HUGGINGFACE_INFERENCE_PROVIDER setting
    
    # Embeddings settings
    EMBEDDINGS_MODEL: str = "text-embedding-3-small"  # OpenAI default
    # For HuggingFace embeddings: "sentence-transformers/all-MiniLM-L6-v2" (22.7M params, lightweight, perfect for laptops)
    # Alternative: "BAAI/bge-small-en-v1.5" (33.4M params, slightly better quality)
    EMBEDDINGS_PROVIDER: Optional[LLMProvider] = None  # If None, uses LLM_PROVIDER
    # Local embeddings configuration (for HuggingFace embeddings)
    EMBEDDINGS_USE_LOCAL: bool = False  # Use local embeddings model instead of API
    EMBEDDINGS_DEVICE: str = "cpu"  # Device for local embeddings: "cpu", "cuda", "cuda:0", etc.
    EMBEDDINGS_MODEL_KWARGS: Optional[str] = None  # JSON string for additional model_kwargs (e.g., '{"device_map":"auto"}')
    
    # Policy Engine Configuration
    POLICY_ENABLED: bool = True  # Feature flag to enable/disable policy engine
    POLICY_RULES_DIR: Path = Path("app/policies")  # Directory containing YAML policy files
    POLICY_RULES_PATTERN: str = "*.yaml"  # File pattern for policy rule files
    POLICY_ENGINE_VENDOR: Optional[str] = None  # Policy engine implementation (e.g., "aspasia", "custom")
    POLICY_AUTO_RELOAD: bool = False  # Auto-reload policies on file change (development only)
    
    # x402 Payment Engine Configuration
    X402_ENABLED: bool = True  # Feature flag to enable/disable x402 payments
    X402_FACILITATOR_URL: str = "https://facilitator.x402.org"  # x402 facilitator service URL
    X402_NETWORK: str = "base"  # Blockchain network (base, ethereum, etc.)
    X402_TOKEN: str = "USDC"  # Token symbol (USDC, USDT, etc.)
    
    # Audio Transcription (STT) Configuration
    STT_API_URL: Optional[str] = None  # Gradio Space URL (default: nvidia/canary-1b-v2)
    STT_SOURCE_LANG: str = "en"  # Source language code for transcription
    STT_TARGET_LANG: str = "en"  # Target language code for transcription
    
    # Image OCR Configuration
    OCR_API_URL: Optional[str] = None  # Gradio Space URL (default: prithivMLmods/Multimodal-OCR3)
    
    # ChromaDB Configuration
    CHROMADB_PERSIST_DIR: str = "./chroma_db"  # Directory to persist ChromaDB data
    CHROMADB_SEED_DOCUMENTS_DIR: Optional[str] = None  # Optional directory to load documents into ChromaDB on startup

    # Twilio configuration
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None  
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # Database Configuration
    DATABASE_URL: Optional[str] = None  # PostgreSQL or SQLite connection string
    DATABASE_ENABLED: bool = True  # Feature flag to enable/disable database
    
    # Seeding Configuration
    SEED_PERMISSIONS: bool = False  # Seed permission definitions and role mappings on startup
    SEED_PERMISSIONS_FORCE: bool = False  # Force update existing permissions (use with caution)
    SEED_DEMO_USERS: bool = False  # Seed demo users on startup
    SEED_DEMO_USERS_FORCE: bool = False  # Force update existing demo users (use with caution)
    SEED_AUDITOR: bool = False  # Seed auditor demo user
    SEED_BANKER: bool = False  # Seed banker demo user
    SEED_LAW_OFFICER: bool = False  # Seed law officer demo user
    SEED_ACCOUNTANT: bool = False  # Seed accountant demo user
    SEED_APPLICANT: bool = False  # Seed applicant demo user
    
    @field_validator('DATABASE_URL', mode='before')
    @classmethod
    def validate_database_url(cls, v):
        """Auto-create SQLite URL for development if not provided."""
        if v is None or v == "":
            # Development fallback: use SQLite in project root
            import os
            db_path = os.path.join(os.getcwd(), "creditnexus.db")
            logger = logging.getLogger(__name__)
            logger.warning(
                f"DATABASE_URL not set. Using SQLite fallback: {db_path}\n"
                "For production, set DATABASE_URL to a PostgreSQL connection string."
            )
            return f"sqlite:///{db_path}"
        return v
    
    @field_validator('LLM_PROVIDER', mode='before')
    @classmethod
    def validate_llm_provider(cls, v):
        """Validate LLM provider configuration."""
        if isinstance(v, str):
            try:
                return LLMProvider(v.lower())
            except ValueError:
                raise ValueError(f"Invalid LLM_PROVIDER: {v}. Must be one of: {[p.value for p in LLMProvider]}")
        return v
    
    @field_validator('POLICY_RULES_DIR', mode='before')
    @classmethod
    def validate_policy_rules_dir(cls, v):
        """Convert string path to Path object."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    def get_policy_rules_files(self) -> List[Path]:
        """
        Get list of policy rule YAML files from configured directory.
        
        Returns:
            List of Path objects for policy rule files
        """
        if not self.POLICY_ENABLED:
            return []
        
        rules_dir = Path(self.POLICY_RULES_DIR)
        
        # Resolve path relative to project root if it's a relative path
        if not rules_dir.is_absolute():
            # Try to find project root (where server.py is located)
            import os
            current_dir = Path(os.getcwd())
            # If we're in client directory, go up one level
            if current_dir.name == 'client':
                rules_dir = current_dir.parent / rules_dir
            else:
                rules_dir = current_dir / rules_dir
        
        if not rules_dir.exists():
            logging.getLogger(__name__).warning(f"Policy rules directory does not exist: {rules_dir}")
            return []
        
        # Find all YAML files recursively matching the pattern
        pattern = self.POLICY_RULES_PATTERN
        # Use rglob for recursive search
        rule_files = list(rules_dir.rglob(pattern))
        
        # Also check for .yml extension recursively
        if pattern.endswith('.yaml'):
            rule_files.extend(rules_dir.rglob(pattern.replace('.yaml', '.yml')))
        
        # Remove duplicates and sort for deterministic loading order
        rule_files = sorted(set(rule_files))
        
        logger_instance = logging.getLogger(__name__)
        if rule_files:
            logger_instance.info(f"Found {len(rule_files)} policy rule file(s) in {rules_dir}")
        else:
            logger_instance.warning(f"No policy rule files found in {rules_dir} (searched recursively for {pattern})")
        
        return rule_files
    
    def get_secret_value(self, key: str) -> str:
        """Get the secret value for a given key."""
        if key == "OPENAI_API_KEY":
            return self.OPENAI_API_KEY.get_secret_value()
        elif key == "VLLM_API_KEY" and self.VLLM_API_KEY:
            return self.VLLM_API_KEY.get_secret_value()
        elif key == "HUGGINGFACE_API_KEY" and self.HUGGINGFACE_API_KEY:
            return self.HUGGINGFACE_API_KEY.get_secret_value()
        raise ValueError(f"Unknown secret key: {key}")


# Global settings object
settings = Settings()

