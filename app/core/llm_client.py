"""
LLM Client Abstraction for CreditNexus.

Provides a unified interface for multiple LLM providers (OpenAI, vLLM, HuggingFace)
while maintaining LangChain compatibility. All LLM operations should use this
abstraction instead of directly instantiating provider-specific clients.
"""

import logging
import json
import time
from typing import Optional, Dict, Any
from enum import Enum

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

logger = logging.getLogger(__name__)

# Import metrics (optional - only if metrics are enabled)
try:
    from app.core.metrics import (
        llm_calls_total,
        llm_call_duration_seconds,
        llm_tokens_total,
        llm_cost_total
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Metrics not available for LLM tracking")

# Global LLM configuration (set at startup)
_llm_config: Optional[Dict[str, Any]] = None


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    VLLM = "vllm"
    HUGGINGFACE = "huggingface"


def create_chat_model(
    provider: str,
    model: str,
    temperature: float = 0,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    inference_provider: Optional[str] = None,
    use_local: bool = False,
    **kwargs
) -> BaseChatModel:
    """
    Create a LangChain chat model using the specified provider.
    
    Uses LangChain's native provider support:
    - OpenAI: Uses langchain_openai.ChatOpenAI
    - vLLM: Uses ChatOpenAI with base_url pointing to vLLM server
    - HuggingFace: Uses ChatOpenAI with HF Inference Providers API endpoint
    
    Args:
        provider: One of 'openai', 'vllm', 'huggingface'
        model: Model identifier (e.g., 'gpt-4o', 'meta-llama/Llama-2-7b-chat-hf')
        temperature: Sampling temperature
        api_key: API key for authentication
        base_url: Base URL for API (required for vLLM, optional for others)
        **kwargs: Additional provider-specific arguments
    
    Returns:
        BaseChatModel instance compatible with LangChain
        
    Raises:
        ValueError: If provider is unsupported or required configuration is missing
    """
    provider_lower = provider.lower()
    
    if provider_lower == "openai":
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
            **kwargs
        )
    elif provider_lower == "vllm":
        if not base_url:
            raise ValueError("VLLM_BASE_URL is required for vLLM provider")
        # vLLM exposes OpenAI-compatible API at /v1/chat/completions
        # Ensure base_url ends with /v1
        vllm_base_url = base_url.rstrip('/')
        if not vllm_base_url.endswith('/v1'):
            vllm_base_url = f"{vllm_base_url}/v1"
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url=vllm_base_url,
            api_key=api_key,  # Optional, for auth if vLLM server requires it
            **kwargs
        )
    elif provider_lower == "huggingface":
        # HuggingFace supports two modes:
        # 1. Local models (use_local=True): Load models locally using transformers
        # 2. Inference endpoints (use_local=False, default): Use API-based inference providers
        import os
        
        # Set HUGGINGFACEHUB_API_TOKEN environment variable for authentication
        if api_key:
            os.environ["HUGGINGFACEHUB_API_TOKEN"] = api_key
        
        # Local model mode (load models locally)
        if use_local:
            logger.info("Using local HuggingFace model (not inference endpoint)")
            try:
                from langchain.chat_models import init_chat_model
                
                # Parse model identifier (remove provider if present, not used for local)
                model_identifier = model
                if ":" in model:
                    parts = model.split(":", 1)
                    if len(parts) == 2:
                        model_identifier = parts[0]
                        logger.warning(
                            f"Provider '{parts[1]}' in model name ignored for local model. "
                            f"Using model: '{model_identifier}'"
                        )
                
                # Use init_chat_model for local models
                return init_chat_model(
                    model=model_identifier,
                    model_provider="huggingface",
                    temperature=temperature,
                    **kwargs
                )
            except ImportError:
                raise ValueError(
                    "Local HuggingFace models require langchain and transformers. "
                    "Install with: pip install langchain langchain-huggingface transformers"
                )
        
        # Inference endpoint mode (default) - use API-based inference providers
        # Use OpenAI-compatible endpoint for structured outputs support
        logger.info("Using HuggingFace inference endpoints (API-based) via OpenAI-compatible endpoint")
        
        if not api_key:
            raise ValueError("HUGGINGFACE_API_KEY is required for HuggingFace provider")
        
        # Parse model identifier - support format: "model:provider" or just "model"
        # For HuggingFace router, we need to pass the full model name including provider
        # if specified, so the router can route to the correct provider
        model_for_api = model  # Keep full model name for API call
        model_identifier = model  # Base model identifier for logging
        provider_from_model = None
        
        if ":" in model:
            parts = model.split(":", 1)
            if len(parts) == 2:
                model_identifier = parts[0]
                provider_from_model = parts[1]
                logger.info(
                    f"Extracted provider '{provider_from_model}' from model identifier. "
                    f"Using model: '{model_identifier}' with provider: '{provider_from_model}'"
                )
                # Keep full model:provider format for API call
                model_for_api = model
        
        # Determine provider (priority: model name > inference_provider > kwargs > default)
        selected_provider = None
        if provider_from_model:
            selected_provider = provider_from_model
            logger.info(f"Using provider from model string: {selected_provider}")
        elif inference_provider:
            selected_provider = inference_provider
            logger.info(f"Using provider from config: {selected_provider}")
            # If provider is from config and not in model name, append it
            if ":" not in model_for_api:
                model_for_api = f"{model_for_api}:{selected_provider}"
        elif "provider" in kwargs:
            selected_provider = kwargs.pop("provider")
            logger.info(f"Using provider from kwargs: {selected_provider}")
            # If provider is from kwargs and not in model name, append it
            if ":" not in model_for_api:
                model_for_api = f"{model_for_api}:{selected_provider}"
        else:
            # Default to "auto" which lets HuggingFace router select the provider
            selected_provider = "auto"
            logger.info("Using provider: auto (server-side selection)")
        
        # Build OpenAI-compatible endpoint URL
        # Format: https://router.huggingface.co/v1 (for auto provider selection)
        # For specific providers, use the generic router endpoint and let it handle provider selection
        # The provider is specified via the model name in the format "model:provider"
        if base_url:
            hf_base_url = base_url
        else:
            # Use the generic router endpoint - it will handle provider selection
            # The provider can be specified in the model name (model:provider format)
            hf_base_url = "https://router.huggingface.co/v1"
        
        logger.info(
            f"Using OpenAI-compatible endpoint: {hf_base_url} "
            f"with model: {model_for_api}"
        )
        
        # Use ChatOpenAI with OpenAI-compatible endpoint
        # This supports structured outputs via with_structured_output()
        # Pass the full model name (including provider if specified) to the router
        return ChatOpenAI(
            model=model_for_api,  # Full model name including provider if specified
            temperature=temperature,
            base_url=hf_base_url,
            api_key=api_key,
            **kwargs
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}. Must be one of: {[p.value for p in LLMProvider]}")


def create_embeddings_model(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    use_local: bool = False,
    device: str = "cpu",
    model_kwargs: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Embeddings:
    """
    Create a LangChain embeddings model using the specified provider.
    
    Args:
        provider: One of 'openai', 'huggingface'
        model: Model identifier (for local: model path or HuggingFace model ID)
        api_key: API key for authentication (not needed for local models)
        use_local: If True, use local embeddings model (HuggingFace only)
        device: Device for local embeddings: "cpu", "cuda", "cuda:0", etc.
        model_kwargs: Additional model_kwargs for HuggingFaceEmbeddings (e.g., {"device_map": "auto"})
        **kwargs: Additional provider-specific arguments
    
    Returns:
        Embeddings instance compatible with LangChain
        
    Raises:
        ValueError: If provider is unsupported or required configuration is missing
    """
    provider_lower = provider.lower()
    
    if provider_lower == "openai":
        return OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            **kwargs
        )
    elif provider_lower == "huggingface":
        # Use langchain_huggingface for native HF embeddings support
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            # Fallback: Use OpenAI-compatible endpoint if langchain_huggingface not available
            logger.warning(
                "langchain_huggingface not available, using OpenAI-compatible endpoint for HuggingFace embeddings"
            )
            if use_local:
                raise ValueError(
                    "Local embeddings require langchain_huggingface. "
                    "Install with: pip install langchain-huggingface"
                )
            return OpenAIEmbeddings(
                model=model,
                base_url="https://api-inference.huggingface.co/v1",
                openai_api_key=api_key,
                **kwargs
            )
        
        # Configure for local or API-based embeddings
        if use_local:
            # Local embeddings: model is loaded locally using sentence-transformers
            # Set up model_kwargs for device configuration
            local_model_kwargs = model_kwargs or {}
            
            # Handle device parameter: convert "auto" to actual device
            actual_device = device
            if device == "auto":
                # Auto-detect device: use cuda if available, else cpu
                try:
                    import torch
                    actual_device = "cuda" if torch.cuda.is_available() else "cpu"
                    logger.info(f"Auto-detected device: {actual_device} (CUDA available: {torch.cuda.is_available()})")
                except ImportError:
                    actual_device = "cpu"
                    logger.warning("PyTorch not available, defaulting to CPU")
            
            if "device" not in local_model_kwargs:
                local_model_kwargs["device"] = actual_device
            
            # Set HUGGINGFACEHUB_API_TOKEN if provided (needed for downloading models)
            import os
            if api_key:
                os.environ["HUGGINGFACEHUB_API_TOKEN"] = api_key
            
            logger.info(
                f"Using local HuggingFace embeddings: model={model}, device={actual_device}"
            )
            
            return HuggingFaceEmbeddings(
                model_name=model,
                model_kwargs=local_model_kwargs,
                **kwargs
            )
        else:
            # API-based embeddings: use HuggingFace Inference API
            # Note: HuggingFaceEmbeddings can also work with API if model is on Hub
            # For API-only, we can use the endpoint approach
            if api_key:
                import os
                os.environ["HUGGINGFACEHUB_API_TOKEN"] = api_key
            
            # Try to use local first (will download if needed), fallback to API
            # HuggingFaceEmbeddings will use the API if model is not cached locally
            return HuggingFaceEmbeddings(
                model_name=model,
                **kwargs
            )
    else:
        raise ValueError(f"Unsupported embeddings provider: {provider}. Must be one of: 'openai', 'huggingface'")


def init_llm_config(settings) -> None:
    """
    Initialize global LLM configuration from settings.
    
    This is called once at application startup. It validates provider-specific
    settings and stores the configuration globally for use by get_chat_model()
    and get_embeddings_model().
    
    Args:
        settings: Application settings object (from app.core.config)
        
    Raises:
        ValueError: If required configuration is missing for the selected provider
        RuntimeError: If configuration is invalid
    """
    global _llm_config
    
    # Validate provider-specific settings
    provider = settings.LLM_PROVIDER.value if hasattr(settings.LLM_PROVIDER, 'value') else settings.LLM_PROVIDER
    
    if provider == "vllm" and not settings.VLLM_BASE_URL:
        raise ValueError("VLLM_BASE_URL is required when LLM_PROVIDER=vllm")
    
    if provider == "huggingface" and not settings.HUGGINGFACE_API_KEY:
        raise ValueError("HUGGINGFACE_API_KEY is required when LLM_PROVIDER=huggingface")
    
    # Get API key for provider
    api_key = _get_api_key_for_provider(settings)
    
    # Get base URL for provider
    base_url = _get_base_url_for_provider(settings)
    
    # Store global configuration
    _llm_config = {
        "provider": provider,
        "model": settings.LLM_MODEL,
        "temperature": settings.LLM_TEMPERATURE,
        "api_key": api_key,
        "base_url": base_url,
        "inference_provider": settings.HUGGINGFACE_INFERENCE_PROVIDER if provider == "huggingface" else None,
        "use_local": settings.HUGGINGFACE_USE_LOCAL if provider == "huggingface" else False,
    }
    
    # Embeddings configuration
    embeddings_provider = settings.EMBEDDINGS_PROVIDER
    if embeddings_provider is None:
        embeddings_provider = settings.LLM_PROVIDER
    
    embeddings_provider_value = embeddings_provider.value if hasattr(embeddings_provider, 'value') else embeddings_provider
    
    # Parse model_kwargs if provided as JSON string
    embeddings_model_kwargs = None
    if settings.EMBEDDINGS_MODEL_KWARGS:
        try:
            embeddings_model_kwargs = json.loads(settings.EMBEDDINGS_MODEL_KWARGS)
        except json.JSONDecodeError:
            logger.warning(
                f"Invalid JSON in EMBEDDINGS_MODEL_KWARGS: {settings.EMBEDDINGS_MODEL_KWARGS}. "
                "Ignoring model_kwargs."
            )
    
    _llm_config["embeddings"] = {
        "provider": embeddings_provider_value,
        "model": settings.EMBEDDINGS_MODEL,
        "api_key": _get_embeddings_api_key(settings, embeddings_provider),
        "use_local": settings.EMBEDDINGS_USE_LOCAL,
        "device": settings.EMBEDDINGS_DEVICE,
        "model_kwargs": embeddings_model_kwargs,
    }
    
    logger.info(
        f"LLM client configured: provider={provider}, model={settings.LLM_MODEL}, "
        f"embeddings_provider={embeddings_provider_value}, embeddings_model={settings.EMBEDDINGS_MODEL}"
    )


def _get_api_key_for_provider(settings) -> Optional[str]:
    """Get the appropriate API key for the configured provider."""
    provider = settings.LLM_PROVIDER.value if hasattr(settings.LLM_PROVIDER, 'value') else settings.LLM_PROVIDER
    
    if provider == "openai":
        return settings.OPENAI_API_KEY.get_secret_value()
    elif provider == "vllm":
        return settings.VLLM_API_KEY.get_secret_value() if settings.VLLM_API_KEY else None
    elif provider == "huggingface":
        return settings.HUGGINGFACE_API_KEY.get_secret_value() if settings.HUGGINGFACE_API_KEY else None
    return None


def _get_base_url_for_provider(settings) -> Optional[str]:
    """Get the appropriate base URL for the configured provider."""
    provider = settings.LLM_PROVIDER.value if hasattr(settings.LLM_PROVIDER, 'value') else settings.LLM_PROVIDER
    
    if provider == "vllm":
        return settings.VLLM_BASE_URL
    elif provider == "huggingface":
        return settings.HUGGINGFACE_BASE_URL
    return None


def _get_embeddings_api_key(settings, provider) -> Optional[str]:
    """Get API key for embeddings provider."""
    provider_value = provider.value if hasattr(provider, 'value') else provider
    
    if provider_value == "openai":
        return settings.OPENAI_API_KEY.get_secret_value()
    elif provider_value == "huggingface":
        return settings.HUGGINGFACE_API_KEY.get_secret_value() if settings.HUGGINGFACE_API_KEY else None
    return None


def get_chat_model(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs
) -> BaseChatModel:
    """
    Get a chat model instance using the global configuration.
    
    This is the main function to use throughout the codebase instead of
    directly instantiating ChatOpenAI.
    
    Args:
        model: Override default model (uses LLM_MODEL from config if not provided)
        temperature: Override default temperature (uses LLM_TEMPERATURE from config if not provided)
        **kwargs: Additional arguments passed to the model constructor
    
    Returns:
        BaseChatModel instance ready to use
        
    Raises:
        RuntimeError: If LLM configuration has not been initialized
    """
    if _llm_config is None:
        raise RuntimeError(
            "LLM configuration not initialized. Call init_llm_config() at startup."
        )
    
    return create_chat_model(
        provider=_llm_config["provider"],
        model=model or _llm_config["model"],
        temperature=temperature if temperature is not None else _llm_config["temperature"],
        api_key=_llm_config["api_key"],
        base_url=_llm_config["base_url"],
        inference_provider=_llm_config.get("inference_provider"),
        use_local=_llm_config.get("use_local", False),
        **kwargs
    )


def get_embeddings_model(
    model: Optional[str] = None,
    **kwargs
) -> Embeddings:
    """
    Get an embeddings model instance using the global configuration.
    
    Args:
        model: Override default model (uses EMBEDDINGS_MODEL from config if not provided)
        **kwargs: Additional arguments passed to the embeddings constructor
    
    Returns:
        Embeddings instance ready to use
        
    Raises:
        RuntimeError: If LLM configuration has not been initialized
    """
    if _llm_config is None:
        raise RuntimeError(
            "LLM configuration not initialized. Call init_llm_config() at startup."
        )
    
    embeddings_config = _llm_config["embeddings"]
    return create_embeddings_model(
        provider=embeddings_config["provider"],
        model=model or embeddings_config["model"],
        api_key=embeddings_config["api_key"],
        use_local=embeddings_config.get("use_local", False),
        device=embeddings_config.get("device", "cpu"),
        model_kwargs=embeddings_config.get("model_kwargs"),
        **kwargs
    )


async def invoke_with_metrics(
    model: BaseChatModel,
    messages: Any,
    provider: Optional[str] = None,
    model_name: Optional[str] = None
) -> Any:
    """
    Invoke LLM model with metrics tracking.
    
    This wrapper function tracks LLM calls, duration, tokens, and cost.
    Use this instead of directly calling model.ainvoke() or model.invoke().
    
    Args:
        model: The chat model instance to invoke
        messages: Input messages for the model
        provider: Provider name (e.g., 'openai', 'huggingface') - auto-detected if None
        model_name: Model name (e.g., 'gpt-4o') - auto-detected if None
    
    Returns:
        Model response
    
    Example:
        >>> model = get_chat_model()
        >>> response = await invoke_with_metrics(model, [{"role": "user", "content": "Hello"}])
    """
    if not METRICS_AVAILABLE:
        # If metrics not available, just call the model directly
        return await model.ainvoke(messages)
    
    # Auto-detect provider and model if not provided
    if provider is None:
        provider = _llm_config["provider"] if _llm_config else "unknown"
    
    if model_name is None:
        model_name = _llm_config["model"] if _llm_config else "unknown"
    
    start_time = time.time()
    
    try:
        result = await model.ainvoke(messages)
        duration = time.time() - start_time
        
        # Extract token usage and cost
        prompt_tokens = 0
        completion_tokens = 0
        cost = 0.0
        
        # Try to extract token usage from response
        if hasattr(result, 'response_metadata'):
            usage = result.response_metadata.get('token_usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
        
        # Calculate cost (simplified - would need actual pricing tables)
        # This is a placeholder - actual cost calculation should use provider-specific pricing
        if provider == "openai":
            # Rough estimates (would need actual pricing)
            if "gpt-4" in model_name.lower():
                cost = (prompt_tokens / 1000 * 0.03) + (completion_tokens / 1000 * 0.06)
            elif "gpt-3.5" in model_name.lower():
                cost = (prompt_tokens / 1000 * 0.0015) + (completion_tokens / 1000 * 0.002)
        
        # Record metrics
        llm_calls_total.labels(
            provider=provider,
            model=model_name,
            status="success"
        ).inc()
        
        llm_call_duration_seconds.labels(
            provider=provider,
            model=model_name
        ).observe(duration)
        
        if prompt_tokens > 0:
            llm_tokens_total.labels(
                provider=provider,
                model=model_name,
                type="input"
            ).inc(prompt_tokens)
        
        if completion_tokens > 0:
            llm_tokens_total.labels(
                provider=provider,
                model=model_name,
                type="output"
            ).inc(completion_tokens)
        
        if cost > 0:
            llm_cost_total.labels(
                provider=provider,
                model=model_name
            ).inc(cost)
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        
        # Determine error status
        error_status = "error"
        if "rate limit" in str(e).lower() or "429" in str(e):
            error_status = "rate_limited"
        
        # Record error metrics
        llm_calls_total.labels(
            provider=provider,
            model=model_name,
            status=error_status
        ).inc()
        
        llm_call_duration_seconds.labels(
            provider=provider,
            model=model_name
        ).observe(duration)
        
        raise









