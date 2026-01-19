"""Configuration management using pydantic-settings for type-safe environment variables."""

import logging
import os
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional, List
from pydantic import SecretStr, field_validator, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

from app.models.cdm import Currency

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
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
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
    HUGGINGFACE_BASE_URL: Optional[str] = (
        None  # Defaults to https://api-inference.huggingface.co/v1
    )
    # For HuggingFace Inference Providers (Cohere, fal, etc.):
    # Use HUGGINGFACE_BASE_URL=router.huggingface.co/{provider}/v3/openai
    # Or use init_chat_model with model_provider="huggingface" and provider parameter
    HUGGINGFACE_INFERENCE_PROVIDER: Optional[str] = (
        "novita"  # Default: "novita" (preferred provider)
    )
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
    EMBEDDINGS_MODEL_KWARGS: Optional[str] = (
        None  # JSON string for additional model_kwargs (e.g., '{"device_map":"auto"}')
    )

    # Policy Engine Configuration
    POLICY_ENABLED: bool = True  # Feature flag to enable/disable policy engine
    POLICY_RULES_DIR: Path = Path("app/policies")  # Directory containing YAML policy files
    POLICY_RULES_PATTERN: str = "*.yaml"  # File pattern for policy rule files
    POLICY_ENGINE_VENDOR: Optional[str] = (
        None  # Policy engine implementation (e.g., "aspasia", "custom")
    )
    POLICY_AUTO_RELOAD: bool = False  # Auto-reload policies on file change (development only)

    # LangChain Configuration for Filing/Signature Chains
    FILING_CHAIN_TEMPERATURE: float = Field(default=0.0, description="Temperature for filing chains")
    SIGNATURE_CHAIN_TEMPERATURE: float = Field(default=0.0, description="Temperature for signature chains")
    FILING_CHAIN_MAX_RETRIES: int = Field(default=3, description="Max retries for filing chains")
    SIGNATURE_CHAIN_MAX_RETRIES: int = Field(default=3, description="Max retries for signature chains")

    # DigiSigner API Configuration
    DIGISIGNER_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="DigiSigner API key for digital signatures"
    )
    DIGISIGNER_BASE_URL: str = Field(
        default="https://api.digisigner.com/v1",
        description="DigiSigner API base URL"
    )
    DIGISIGNER_WEBHOOK_SECRET: Optional[SecretStr] = Field(
        default=None,
        description="DigiSigner webhook secret for signature status updates"
    )

    # Companies House API Configuration
    COMPANIES_HOUSE_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Companies House API key for UK filings (free registration)"
    )

    # x402 Payment Engine Configuration
    X402_ENABLED: bool = True  # Feature flag to enable/disable x402 payments
    X402_FACILITATOR_URL: str = "https://facilitator.x402.org"  # x402 facilitator service URL
    X402_NETWORK: str = "base"  # Blockchain network (base, ethereum, etc.)
    X402_TOKEN: str = "USDC"  # Token symbol (USDC, USDT, etc.)
    X402_NETWORK_RPC_URL: str = Field(
        default="https://mainnet.base.org",
        description="RPC URL for Base network (use https://sepolia.base.org for testnet)"
    )

    # Securitization Smart Contracts (Base network)
    # If empty, contracts will be auto-deployed on first use
    SECURITIZATION_NOTARIZATION_CONTRACT: str = Field(
        default="",
        description="SecuritizationNotarization contract address (auto-deployed if empty)"
    )
    SECURITIZATION_TOKEN_CONTRACT: str = Field(
        default="",
        description="SecuritizationToken (ERC-721) contract address (auto-deployed if empty)"
    )
    SECURITIZATION_PAYMENT_ROUTER_CONTRACT: str = Field(
        default="",
        description="SecuritizationPaymentRouter contract address (auto-deployed if empty)"
    )
    
    # USDC Token Address (Base network)
    USDC_TOKEN_ADDRESS: str = Field(
        default="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        description="USDC token address on Base network"
    )
    
    # Smart Contract Auto-Deployment
    BLOCKCHAIN_DEPLOYER_PRIVATE_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Private key for contract deployment (auto-generated in dev if not provided)"
    )
    BLOCKCHAIN_AUTO_DEPLOY: bool = Field(
        default=True,
        description="Auto-deploy contracts if addresses not in config"
    )
    
    # Wallet Auto-Generation
    WALLET_AUTO_GENERATE_DEMO: bool = Field(
        default=True,
        description="Auto-generate demo wallet addresses for users without wallets"
    )

    # Notarization Payment Configuration
    NOTARIZATION_FEE_ENABLED: bool = Field(
        default=True,
        description="Feature flag to enable/disable notarization fees"
    )
    NOTARIZATION_FEE_AMOUNT: Decimal = Field(
        default=Decimal("50.00"),
        description="Default notarization fee in USD"
    )
    NOTARIZATION_FEE_CURRENCY: Currency = Field(
        default=Currency.USD,
        description="Notarization fee currency"
    )
    NOTARIZATION_FEE_ADMIN_SKIP: bool = Field(
        default=True,
        description="Allow admin users to skip payment requirement"
    )

    # Audio Transcription (STT) Configuration
    STT_API_URL: Optional[str] = None  # Gradio Space URL (default: nvidia/canary-1b-v2)
    STT_SOURCE_LANG: str = "en"  # Source language code for transcription
    STT_TARGET_LANG: str = "en"  # Target language code for transcription

    # Image OCR Configuration
    OCR_API_URL: Optional[str] = None  # Gradio Space URL (default: prithivMLmods/Multimodal-OCR3)

    # Web Search Configuration (vendored from dev/app.py)
    SERPER_API_KEY: Optional[SecretStr] = None  # Serper API key for web search
    WEB_SEARCH_RATE_LIMIT: str = "360/hour"  # Rate limit for web search
    WEB_SEARCH_ANALYTICS_DIR: Optional[Path] = None  # Analytics data directory

    # Reranking Configuration
    RERANKING_USE_LOCAL: bool = False  # Use local reranking model instead of API
    RERANKING_MODEL: str = "BAAI/bge-reranker-base"  # Local reranking model
    RERANKING_DEVICE: str = "cpu"  # Device for local reranking: "cpu", "cuda", "cuda:0"
    RERANKING_API_URL: Optional[str] = None  # Remote reranking API URL (e.g., Cohere, Jina)
    RERANKING_API_KEY: Optional[SecretStr] = None  # Remote reranking API key

    # LangAlpha Quantitative Analysis Configuration
    POLYGON_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Polygon.io API key for market data (get from https://polygon.io/)"
    )
    ALPHA_VANTAGE_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Alpha Vantage API key for fundamental data (get from https://www.alphavantage.co/support/#api-key)"
    )
    TAVILY_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Tavily API key for news/search (get from https://tavily.com/)"
    )
    TICKERTICK_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Tickertick API key for financial news (NOTE: This service may not be publicly available. Leave unset to use alternative news sources like web_search tool or Tavily.)"
    )
    # LangAlpha LLM Configuration (for different agent types)
    LANGALPHA_REASONING_MODEL: str = Field(
        default="gpt-4o",
        description="LLM model for reasoning tasks (supervisor, planner, analyst)"
    )
    LANGALPHA_BASIC_MODEL: str = Field(
        default="gpt-4o-mini",
        description="LLM model for basic tasks (researcher, reporter, market)"
    )
    LANGALPHA_ECONOMIC_MODEL: str = Field(
        default="gpt-4o-mini",
        description="LLM model for economic analysis tasks"
    )
    LANGALPHA_CODING_MODEL: str = Field(
        default="gpt-4o",
        description="LLM model for coding/calculation tasks"
    )
    LANGALPHA_BUDGET_LEVEL: str = Field(
        default="medium",
        description="Budget level for LangAlpha agents: 'low', 'medium', 'high'"
    )

    # ChromaDB Configuration
    CHROMADB_PERSIST_DIR: str = "./chroma_db"  # Directory to persist ChromaDB data
    CHROMADB_SEED_DOCUMENTS_DIR: Optional[str] = (
        None  # Optional directory to load documents into ChromaDB on startup
    )

    # Enhanced Satellite Verification & Green Finance
    ENHANCED_SATELLITE_ENABLED: bool = True
    STREET_MAP_API_PROVIDER: str = "openstreetmap"  # Only OSM, no Google/Mapbox

    # OpenStreetMap Configuration
    OSM_OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    OSM_CACHE_ENABLED: bool = True
    OSM_CACHE_TTL_HOURS: int = 24

    # Air Quality Configuration
    AIR_QUALITY_ENABLED: bool = True
    AIR_QUALITY_API_PROVIDER: str = "openaq"  # openaq only (free)
    AIR_QUALITY_API_KEY: Optional[str] = None  # Not required for OpenAQ free tier
    AIR_QUALITY_CACHE_ENABLED: bool = True
    AIR_QUALITY_CACHE_TTL_HOURS: int = 24

    # Vehicle Detection (Selective - High Cost)
    VEHICLE_DETECTION_ENABLED: bool = False  # Default: disabled, enable for high-value cases
    VEHICLE_DETECTION_MODEL_PATH: str = "./models/vehicle_detector.pt"
    VEHICLE_DETECTION_MIN_TRANSACTION_AMOUNT: float = 1000000.0  # Only process if amount > $1M
    VEHICLE_DETECTION_USE_HIGH_RES_IMAGERY: bool = True

    # Pollution Monitoring
    POLLUTION_MONITORING_ENABLED: bool = True
    METHANE_MONITORING_ENABLED: bool = True
    METHANE_USE_SENTINEL5P: bool = True  # Free, coarse resolution

    # Sustainability Scoring
    SUSTAINABILITY_SCORING_ENABLED: bool = True
    SUSTAINABILITY_NDVI_WEIGHT: float = 0.25
    SUSTAINABILITY_AQI_WEIGHT: float = 0.25
    SUSTAINABILITY_ACTIVITY_WEIGHT: float = 0.20
    SUSTAINABILITY_GREEN_INFRA_WEIGHT: float = 0.15
    SUSTAINABILITY_POLLUTION_WEIGHT: float = 0.15

    # Twilio configuration
    TWILIO_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: Optional[SecretStr] = None
    TWILIO_AUTH_TOKEN: Optional[SecretStr] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    TWILIO_SMS_ENABLED: bool = True
    TWILIO_VOICE_ENABLED: bool = True
    TWILIO_WEBHOOK_URL: Optional[str] = None

    @model_validator(mode='after')
    def validate_twilio_credentials(self):
        """Validate that Twilio credentials are present if Twilio is enabled."""
        if self.TWILIO_ENABLED:
            if not self.TWILIO_ACCOUNT_SID:
                raise ValueError("TWILIO_ACCOUNT_SID is required when TWILIO_ENABLED is True")
            if not self.TWILIO_AUTH_TOKEN:
                raise ValueError("TWILIO_AUTH_TOKEN is required when TWILIO_ENABLED is True")
        return self

    # Remote API Configuration
    REMOTE_API_ENABLED: bool = False
    REMOTE_API_PORT: int = 8443
    REMOTE_API_SSL_CERT_PATH: Optional[Path] = None
    REMOTE_API_SSL_KEY_PATH: Optional[Path] = None
    REMOTE_API_SSL_CERT_CHAIN_PATH: Optional[Path] = None
    REMOTE_API_ALLOWED_IPS: Optional[List[str]] = None
    REMOTE_API_ALLOWED_CIDRS: Optional[List[str]] = None

    # Verification Configuration
    VERIFICATION_LINK_EXPIRY_HOURS: int = 72
    VERIFICATION_BASE_URL: Optional[str] = None
    LINK_ENCRYPTION_KEY: Optional[SecretStr] = None  # Fernet key for link encryption
    VERIFICATION_FILE_CONFIG_PATH: Optional[Path] = None  # YAML config for file whitelist
    
    # Workflow Delegation Configuration
    WORKFLOW_DELEGATION_BASE_URL: Optional[str] = None  # Base URL for workflow delegation links (e.g., "https://josephrp.github.io/creditnexus")

    
    # Demo Data Configuration
    DEMO_DATA_ENABLED: bool = True  # Feature flag to enable/disable demo data generation
    DEMO_DATA_DEAL_COUNT: int = 12  # Default number of deals to generate
    DEMO_DATA_DEAL_TYPES: List[str] = ["loan_application", "refinancing", "restructuring"]  # Available deal types
    DEMO_DATA_STORAGE_PATH: str = "storage/deals/demo"  # Storage path for demo deal files
    DEMO_DATA_CACHE_ENABLED: bool = True  # Enable caching for generated CDM data
    DEMO_DATA_CACHE_TTL: int = 86400  # Cache TTL in seconds (default: 24 hours)
    DEMO_DATA_CACHE_PATH: Optional[str] = None  # Optional path for cache database (default: in-memory)
    
    # Database Configuration
    DATABASE_URL: Optional[str] = None  # PostgreSQL or SQLite connection string
    DATABASE_ENABLED: bool = True  # Feature flag to enable/disable database

    # Database SSL/TLS Configuration
    DB_SSL_MODE: str = "prefer"  # SSL mode: disable, allow, prefer, require, verify-ca, verify-full
    DB_SSL_CA_CERT: Optional[str] = None  # Path to CA certificate file
    DB_SSL_CLIENT_CERT: Optional[str] = None  # Path to client certificate file (mutual TLS)
    DB_SSL_CLIENT_KEY: Optional[str] = None  # Path to client private key file (mutual TLS)
    DB_SSL_REQUIRED: bool = False  # Require SSL in production (enforced if True)

    # Automatic Certificate Generation for Database SSL
    DB_SSL_AUTO_GENERATE: bool = True  # Auto-generate certificates if not provided
    DB_SSL_AUTO_GENERATE_CA: bool = True  # Auto-generate CA certificate
    DB_SSL_AUTO_GENERATE_CLIENT: bool = False  # Auto-generate client cert (mutual TLS)
    DB_SSL_AUTO_CERT_DIR: str = "./ssl_certs/db"  # Directory for auto-generated certificates
    DB_SSL_AUTO_CERT_VALIDITY_DAYS: int = 365  # Certificate validity period (1 year default)

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
    
    # Security Configuration
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5000", "http://localhost:8000", "https://josephrp.github.io", "null"]  # "null" = Origin for file:// (Electron loadFile); 5000 = Vite PM2 dev
    CORS_ALLOW_CREDENTIALS: bool = True  # Allow credentials in CORS
    SESSION_SAME_SITE: str = "strict"  # Session cookie same-site policy: "strict", "lax", or "none"
    SESSION_SECURE: bool = True  # Require HTTPS for session cookies
    SESSION_MAX_AGE: int = 86400 * 7  # Session max age in seconds (7 days)
    RATE_LIMIT_ENABLED: bool = True  # Enable rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60  # Requests per minute per IP
    RATE_LIMIT_PER_HOUR: int = 1000  # Requests per hour per IP (for additional protection)
    SECURITY_HEADERS_ENABLED: bool = True  # Enable security headers middleware
    JWT_SECRET_KEY: Optional[SecretStr] = None  # JWT secret key (required in production)
    JWT_REFRESH_SECRET_KEY: Optional[SecretStr] = None  # JWT refresh secret key (required in production)
    
    # Prometheus Metrics Configuration
    METRICS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
    METRICS_PATH: str = Field(default="/metrics", description="Metrics endpoint path")
    SYSTEM_METRICS_ENABLED: bool = Field(default=False, description="Enable system metrics (requires psutil)")
    METRICS_COLLECT_INTERVAL: int = Field(default=60, description="System metrics collection interval (seconds)")
    
    # Encryption at Rest Configuration
    ENCRYPTION_KEY: Optional[SecretStr] = None  # Master encryption key for data at rest (Fernet key or password)
    ENCRYPTION_ENABLED: bool = True  # Enable encryption for sensitive fields
    ENCRYPTION_AUTO_ENCRYPT_FIELDS: bool = True  # Automatically encrypt sensitive fields in JSONB
    
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

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def validate_llm_provider(cls, v):
        """Validate LLM provider configuration."""
        if isinstance(v, str):
            try:
                return LLMProvider(v.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid LLM_PROVIDER: {v}. Must be one of: {[p.value for p in LLMProvider]}"
                )
        return v

    @field_validator("ENCRYPTION_KEY", mode="before")
    @classmethod
    def validate_encryption_key(cls, v):
        """Validate encryption key format."""
        logger = logging.getLogger(__name__)
        if v is None or v == "":
            return None
        # Fernet keys are 44 bytes when base64-encoded
        if isinstance(v, str):
            if len(v) != 44:
                logger.warning(
                    f"ENCRYPTION_KEY length is {len(v)}, expected 44 (base64-encoded Fernet key). "
                    "A new key will be generated on first use."
                )
            return v
        return v
    
    @field_validator("POLICY_RULES_DIR", mode="before")
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
            if current_dir.name == "client":
                rules_dir = current_dir.parent / rules_dir
            else:
                rules_dir = current_dir / rules_dir

        if not rules_dir.exists():
            logging.getLogger(__name__).warning(
                f"Policy rules directory does not exist: {rules_dir}"
            )
            return []

        # Find all YAML files recursively matching the pattern
        pattern = self.POLICY_RULES_PATTERN
        # Use rglob for recursive search
        rule_files = list(rules_dir.rglob(pattern))

        # Also check for .yml extension recursively
        if pattern.endswith(".yaml"):
            rule_files.extend(rules_dir.rglob(pattern.replace(".yaml", ".yml")))

        # Remove duplicates and sort for deterministic loading order
        rule_files = sorted(set(rule_files))

        logger_instance = logging.getLogger(__name__)
        if rule_files:
            logger_instance.info(f"Found {len(rule_files)} policy rule file(s) in {rules_dir}")
        else:
            logger_instance.warning(
                f"No policy rule files found in {rules_dir} (searched recursively for {pattern})"
            )

        return rule_files

    def validate_ssl_config(self) -> None:
        """Validate SSL configuration at startup.
        
        This method validates that SSL configuration is correct and consistent.
        It should be called during application startup to ensure proper SSL setup.
        
        Raises:
            ValueError: If SSL configuration is invalid or inconsistent.
            
        Examples:
            >>> settings = Settings(DB_SSL_REQUIRED=True, DB_SSL_MODE="verify-full")
            >>> settings.validate_ssl_config()  # Raises ValueError if DB_SSL_CA_CERT not set
        """
        import os
        from pathlib import Path
        
        # Check if SSL is required
        if self.DB_SSL_REQUIRED:
            if not self.DB_SSL_MODE or self.DB_SSL_MODE == "disable":
                raise ValueError(
                    "DB_SSL_REQUIRED=true but DB_SSL_MODE is not set or is 'disable'. "
                    "Set DB_SSL_MODE to 'require', 'verify-ca', or 'verify-full'."
                )
            
            # Check for insecure SSL modes when SSL is required
            if self.DB_SSL_MODE in ["disable", "allow"]:
                raise ValueError(
                    f"DB_SSL_REQUIRED=true but DB_SSL_MODE={self.DB_SSL_MODE} is not secure. "
                    "Use 'require', 'verify-ca', or 'verify-full'."
                )
            
            # Check certificate requirements for verification modes
            if self.DB_SSL_MODE in ["verify-ca", "verify-full"]:
                if not self.DB_SSL_CA_CERT:
                    # Check if auto-generation is enabled
                    if not self.DB_SSL_AUTO_GENERATE:
                        raise ValueError(
                            f"DB_SSL_MODE={self.DB_SSL_MODE} requires DB_SSL_CA_CERT to be set, "
                            "or enable DB_SSL_AUTO_GENERATE=true."
                        )
                elif not Path(self.DB_SSL_CA_CERT).exists():
                    # Check if auto-generation will create it
                    if not self.DB_SSL_AUTO_GENERATE:
                        raise ValueError(
                            f"DB_SSL_CA_CERT file not found: {self.DB_SSL_CA_CERT}. "
                            "Enable DB_SSL_AUTO_GENERATE=true to auto-generate certificates."
                        )
        
        # Validate client certificate configuration (mutual TLS)
        if self.DB_SSL_CLIENT_CERT or self.DB_SSL_CLIENT_KEY:
            if not self.DB_SSL_CLIENT_CERT:
                raise ValueError(
                    "DB_SSL_CLIENT_KEY is set but DB_SSL_CLIENT_CERT is missing. "
                    "Both must be provided for mutual TLS."
                )
            if not self.DB_SSL_CLIENT_KEY:
                raise ValueError(
                    "DB_SSL_CLIENT_CERT is set but DB_SSL_CLIENT_KEY is missing. "
                    "Both must be provided for mutual TLS."
                )
            
            # Check if client certificate files exist
            if self.DB_SSL_CLIENT_CERT and not Path(self.DB_SSL_CLIENT_CERT).exists():
                if not self.DB_SSL_AUTO_GENERATE_CLIENT:
                    raise ValueError(
                        f"DB_SSL_CLIENT_CERT file not found: {self.DB_SSL_CLIENT_CERT}. "
                        "Enable DB_SSL_AUTO_GENERATE_CLIENT=true to auto-generate client certificate."
                    )
            
            if self.DB_SSL_CLIENT_KEY and not Path(self.DB_SSL_CLIENT_KEY).exists():
                if not self.DB_SSL_AUTO_GENERATE_CLIENT:
                    raise ValueError(
                        f"DB_SSL_CLIENT_KEY file not found: {self.DB_SSL_CLIENT_KEY}. "
                        "Enable DB_SSL_AUTO_GENERATE_CLIENT=true to auto-generate client key."
                    )
        
        # Validate SSL mode value
        valid_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        if self.DB_SSL_MODE not in valid_modes:
            raise ValueError(
                f"Invalid DB_SSL_MODE: {self.DB_SSL_MODE}. "
                f"Must be one of: {', '.join(valid_modes)}"
            )

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
