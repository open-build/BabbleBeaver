"""
LLM Manager for multi-provider support with fallback capabilities.
Supports Gemini, OpenAI, DigitalOcean, and other hosted LLM providers.
"""

import os
import logging
import sys
from typing import Optional, List, Dict, Callable, Any
from enum import Enum
import openai
import google.generativeai as genai

# Try to import Vertex AI (optional)
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    VERTEXAI_AVAILABLE = True
except ImportError:
    VERTEXAI_AVAILABLE = False
    vertexai = None
    GenerativeModel = None

# Try to import DigitalOcean agent (optional)
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))
    from digitalocean import DigitalOceanAgent
    DIGITALOCEAN_AVAILABLE = True
except ImportError:
    DIGITALOCEAN_AVAILABLE = False
    DigitalOceanAgent = None

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    DIGITALOCEAN = "digitalocean"


class LLMConfig:
    """Configuration for an LLM provider."""
    
    def __init__(
        self,
        provider: LLMProvider,
        model_name: str,
        api_key: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        priority: int = 0,
        enabled: bool = True
    ):
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.priority = priority  # Lower number = higher priority
        self.enabled = enabled
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary (without exposing API key)."""
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "priority": self.priority,
            "enabled": self.enabled,
            "api_key_configured": bool(self.api_key)
        }


class LLMManager:
    """
    Manages multiple LLM providers with automatic fallback.
    Attempts providers in priority order until one succeeds.
    """
    
    def __init__(self):
        self.providers: List[LLMConfig] = []
        self._initialize_from_env()
    
    def _initialize_from_env(self):
        """Initialize provider configurations from environment variables."""
        # Check if using Vertex AI (GCP) or standard Gemini API
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION", "us-west1")
        
        # Gemini configuration
        gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        # Use Vertex AI if PROJECT_ID is set and vertexai is available
        if project_id and VERTEXAI_AVAILABLE:
            logger.info(f"Initializing Vertex AI with project: {project_id}, location: {location}")
            vertexai.init(project=project_id, location=location)
            gemini_model = os.getenv("VERTEX_MODEL_NAME") or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
            self.add_provider(LLMConfig(
                provider=LLMProvider.GEMINI,
                model_name=gemini_model,
                api_key=gemini_key or "vertex-ai",  # Vertex AI doesn't need API key
                priority=int(os.getenv("GEMINI_PRIORITY", "0")),
                enabled=os.getenv("GEMINI_ENABLED", "true").lower() == "true"
            ))
        elif gemini_key:
            logger.info("Initializing standard Gemini API")
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            self.add_provider(LLMConfig(
                provider=LLMProvider.GEMINI,
                model_name=gemini_model,
                api_key=gemini_key,
                priority=int(os.getenv("GEMINI_PRIORITY", "0")),
                enabled=os.getenv("GEMINI_ENABLED", "true").lower() == "true"
            ))
            genai.configure(api_key=gemini_key)
        
        # OpenAI configuration
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            self.add_provider(LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name=openai_model,
                api_key=openai_key,
                priority=int(os.getenv("OPENAI_PRIORITY", "1")),
                enabled=os.getenv("OPENAI_ENABLED", "true").lower() == "true"
            ))
            openai.api_key = openai_key
        
        # HuggingFace configuration (placeholder for future implementation)
        hf_key = os.getenv("HUGGINGFACE_AUTH_TOKEN")
        if hf_key:
            hf_model = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-2-7b-chat-hf")
            self.add_provider(LLMConfig(
                provider=LLMProvider.HUGGINGFACE,
                model_name=hf_model,
                api_key=hf_key,
                priority=int(os.getenv("HUGGINGFACE_PRIORITY", "2")),
                enabled=os.getenv("HUGGINGFACE_ENABLED", "false").lower() == "true"
            ))
        
        # DigitalOcean Gradient AI Platform configuration
        do_token = os.getenv("DIGITALOCEAN_API_TOKEN")
        do_url = os.getenv("DIGITALOCEAN_AGENT_URL")
        if do_token and do_url:
            self.add_provider(LLMConfig(
                provider=LLMProvider.DIGITALOCEAN,
                model_name=do_url,  # Store agent URL as model_name
                api_key=do_token,
                priority=int(os.getenv("DIGITALOCEAN_PRIORITY", "3")),
                enabled=os.getenv("DIGITALOCEAN_AGENT_ENABLED", "false").lower() == "true"
            ))
        
        # Sort providers by priority
        self.providers.sort(key=lambda x: x.priority)
    
    def add_provider(self, config: LLMConfig):
        """Add a new provider configuration."""
        self.providers.append(config)
        self.providers.sort(key=lambda x: x.priority)
    
    def remove_provider(self, provider: LLMProvider):
        """Remove a provider by type."""
        self.providers = [p for p in self.providers if p.provider != provider]
    
    def get_provider_config(self, provider: LLMProvider) -> Optional[LLMConfig]:
        """Get configuration for a specific provider."""
        for config in self.providers:
            if config.provider == provider and config.enabled:
                return config
        return None
    
    def list_providers(self) -> List[Dict]:
        """List all configured providers."""
        return [p.to_dict() for p in self.providers]
    
    def _call_gemini(self, config: LLMConfig, prompt: str, **kwargs) -> str:
        """Call Gemini API (standard or Vertex AI)."""
        try:
            # Check if using Vertex AI
            project_id = os.getenv("PROJECT_ID")
            
            if project_id and VERTEXAI_AVAILABLE:
                # Use Vertex AI
                model = GenerativeModel(config.model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={
                        'max_output_tokens': kwargs.get('max_tokens', config.max_tokens),
                        'temperature': kwargs.get('temperature', config.temperature)
                    }
                )
                return response.text
            else:
                # Use standard Gemini API
                model = genai.GenerativeModel(config.model_name)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        max_output_tokens=kwargs.get('max_tokens', config.max_tokens),
                        temperature=kwargs.get('temperature', config.temperature)
                    )
                )
                return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def _call_openai(self, config: LLMConfig, prompt: str, **kwargs) -> str:
        """Call OpenAI API."""
        try:
            client = openai.OpenAI(api_key=config.api_key)
            response = client.chat.completions.create(
                model=config.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get('max_tokens', config.max_tokens),
                temperature=kwargs.get('temperature', config.temperature)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _call_huggingface(self, config: LLMConfig, prompt: str, **kwargs) -> str:
        """Call HuggingFace Inference API (placeholder)."""
        # TODO: Implement HuggingFace inference
        raise NotImplementedError("HuggingFace inference not yet implemented")
    
    def _call_digitalocean(self, config: LLMConfig, prompt: str, **kwargs) -> str:
        """Call DigitalOcean Gradient AI Platform agent."""
        if not DIGITALOCEAN_AVAILABLE:
            raise Exception("DigitalOcean agent module not available")
        
        try:
            import asyncio
            
            # Create agent with stored configuration
            agent = DigitalOceanAgent(
                api_token=config.api_key,
                agent_url=config.model_name,  # URL is stored in model_name
                timeout=kwargs.get('timeout', 30.0)
            )
            
            # Get context from kwargs if provided
            context = kwargs.get('context', None)
            
            # Call agent (async)
            response = asyncio.run(agent.chat_completion(
                prompt=prompt,
                context=context,
                stream=False
            ))
            
            if not response:
                raise Exception("DigitalOcean agent returned no response")
            
            return response
            
        except Exception as e:
            logger.error(f"DigitalOcean agent error: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using available LLM providers with fallback.
        
        Args:
            prompt: The prompt to send to the LLM
            preferred_provider: Optional preferred provider to try first
            **kwargs: Additional parameters (max_tokens, temperature, etc.)
            
        Returns:
            Dictionary with response text and metadata
            
        Raises:
            Exception: If all providers fail
        """
        providers_to_try = self.providers.copy()
        
        # If preferred provider specified, try it first
        if preferred_provider:
            config = self.get_provider_config(preferred_provider)
            if config:
                providers_to_try = [config] + [p for p in providers_to_try if p.provider != preferred_provider]
        
        # Filter to only enabled providers
        providers_to_try = [p for p in providers_to_try if p.enabled]
        
        if not providers_to_try:
            raise Exception("No LLM providers configured or enabled")
        
        last_error = None
        
        for config in providers_to_try:
            try:
                logger.info(f"Attempting to use {config.provider} ({config.model_name})")
                
                if config.provider == LLMProvider.GEMINI:
                    response_text = self._call_gemini(config, prompt, **kwargs)
                elif config.provider == LLMProvider.OPENAI:
                    response_text = self._call_openai(config, prompt, **kwargs)
                elif config.provider == LLMProvider.HUGGINGFACE:
                    response_text = self._call_huggingface(config, prompt, **kwargs)
                elif config.provider == LLMProvider.DIGITALOCEAN:
                    response_text = self._call_digitalocean(config, prompt, **kwargs)
                else:
                    logger.warning(f"Unknown provider: {config.provider}")
                    continue
                
                return {
                    "response": response_text,
                    "provider": config.provider,
                    "model": config.model_name,
                    "success": True
                }
                
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {config.provider} failed: {e}. Trying next provider...")
                continue
        
        # All providers failed
        error_msg = f"All LLM providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def update_provider_config(
        self,
        provider: LLMProvider,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        priority: Optional[int] = None,
        enabled: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ):
        """Update configuration for an existing provider."""
        config = self.get_provider_config(provider)
        
        if not config:
            # Find disabled config or create new one
            for c in self.providers:
                if c.provider == provider:
                    config = c
                    break
            
            if not config:
                raise ValueError(f"Provider {provider} not found")
        
        if model_name is not None:
            config.model_name = model_name
        if api_key is not None:
            config.api_key = api_key
        if priority is not None:
            config.priority = priority
        if enabled is not None:
            config.enabled = enabled
        if max_tokens is not None:
            config.max_tokens = max_tokens
        if temperature is not None:
            config.temperature = temperature
        
        # Re-sort by priority
        self.providers.sort(key=lambda x: x.priority)


# Global LLM manager instance
llm_manager = LLMManager()
