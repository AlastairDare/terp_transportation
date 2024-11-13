from typing import Any
from .base_provider import BaseAIProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from ..utils.exceptions import ConfigurationError

class AIProviderFactory:
    @staticmethod
    def create_provider(ai_config: Any, provider_settings: Any) -> BaseAIProvider:
        """Create appropriate AI provider based on configuration"""
        if ai_config.llm_model_family == "ChatGPT by OpenAI":
            return OpenAIProvider(provider_settings)
        elif ai_config.llm_model_family == "Claude by Anthropic":
            return AnthropicProvider(provider_settings)
        else:
            raise ConfigurationError(f"Unknown AI provider: {ai_config.llm_model_family}")
