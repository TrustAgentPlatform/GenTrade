"""
LLM Provider and Factory Module

This module provides classes for managing Large Language Model (LLM) providers,
their models, and creating instances of custom chat models with tracking capabilities.

Key components:
- ModelInfo: Dataclass storing detailed information about LLM models
- CustomLLMChat: Extended ChatOpenAI class with token tracking and request logging
- LLMProvider: Manages a single LLM service provider and its available models
- LLMFactory: Central factory for managing multiple providers and creating LLM instances

The module supports loading provider configurations from JSON files, tracking token
usage and request metrics, calculating costs, and discovering models across providers.
"""

import os
import time
import logging
import json

from typing import List, Optional, Dict, Set, Tuple, Any
from dataclasses import dataclass
from pydantic import Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage,
    BaseMessage
)
from langchain_core.runnables import RunnableConfig


LOG = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)

@dataclass
class ModelInfo:
    """
    Data class to store detailed information about a specific LLM model.

    Attributes:
        provider_name: Name of the provider offering this model
        model_name: Common human-readable name for the model
        model_type: Classification of the model (e.g., 'chat', 'embedding', 'completion')
        model_path: Provider-specific identifier used in API calls
        input_price: Cost per million input tokens in USD
        output_price: Cost per million output tokens in USD
        max_input_tokens: Maximum number of input tokens allowed
        max_output_tokens: Maximum number of output tokens allowed
        context_window: Total token capacity (input + output)
        description: Optional detailed description of the model's capabilities
    """
    provider_name: str
    model_name: str
    model_type: str
    model_path: str
    input_price: float
    output_price: float
    max_input_tokens: int
    max_output_tokens: int
    context_window: int
    description: Optional[str] = None


class CustomLLMChat(ChatOpenAI):
    """
    Custom LangChain OpenAI subclass with token usage tracking and request logging.
    Overrides the invoke method to implement tracking functionality.
    """
    instance_id: Optional[str] = Field(
        default=None, description="Unique ID for the LLM instance"
    )
    request_logs: List[Dict[str, Any]] = Field(default_factory=list, init=False)

    def __init__(self, *args, instance_id: Optional[str] = None, **kwargs):
        #self.model = kwargs['model']
        super().__init__(*args, **kwargs)
        self.instance_id = instance_id
        self.request_logs = []

    def invoke(
        self,
        input: str | List[BaseMessage],  # pylint: disable=redefined-builtin
        config: RunnableConfig = None,
        **kwargs
    ) -> str | AIMessage:
        """
        Overrides the invoke method to track token usage and log requests

        Args:
            input: Prompt input for the LLM (string or list of messages)
            stop: Stop sequences
            run_manager: Callback manager
            **kwargs: Additional parameters

        Returns:
            Response from the LLM
        """
        # 1. Execute the original call
        start_time = time.perf_counter()
        response = super().invoke(input, config, ** kwargs)
        end_time = time.perf_counter()
        duration_ms = int((end_time - start_time) * 1000)  # Convert to milliseconds

        # 2. Extract prompt text (handle different input types)
        if isinstance(input, str):
            prompt_text = input
        elif isinstance(input, list) and all(isinstance(msg, BaseMessage) for msg in input):
            prompt_text = "\n".join([f"{msg.__class__.__name__}: {msg.content}" for msg in input])
        else:
            prompt_text = str(input)  # Fallback handling

        # 3. Extract response text
        if isinstance(response, AIMessage):
            ai_response = response.content
        else:
            ai_response = str(response)

        # 4. Get token usage (from last call's llm_output)
        # Note: Needs access to internal _last_llm_output attribute, which is a LangChain internal
        # property
        token_usage = self._last_llm_output.get("token_usage", {}) \
            if hasattr(self, '_last_llm_output') else {}
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)

        # 5. Create log entry
        log_entry = {
            "instance_id": self.instance_id,
            "model_name": self.model_name,
            "prompt": prompt_text,
            "ai_response": ai_response,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "request_timestamp": time.time(),
            "request_id": f"req-{self.instance_id}-{int(time.time())}",
            "status": "success",
            "duration": duration_ms
        }

        self.request_logs.append(log_entry)
        LOG.debug(f"Logged LLM request: {log_entry['request_id']} (tokens: {total_tokens} \
            duration(ms): {duration_ms})")

        return response

    # The following methods remain unchanged
    def get_logs(self, clear_after_retrieval: bool = False) -> List[Dict[str, Any]]:
        logs = self.request_logs.copy()
        if clear_after_retrieval:
            self.request_logs = []
            LOG.debug(f"Cleared logs for CustomLLMChat instance: {self.instance_id}")
        return logs

    def clear_logs(self) -> None:
        self.request_logs = []
        LOG.debug(f"Manually cleared logs for CustomLLMChat instance: {self.instance_id}")


class LLMProvider:
    """
    Class representing a single LLM service provider (e.g., OpenAI, Anthropic).

    Manages connection details, authentication, and available models for a
    specific LLM provider.
    """

    def __init__(self,
                 name: str,
                 base_url: str,
                 api_key: Optional[str] = None,
                 models: Optional[Dict[str, ModelInfo]] = None):
        """
        Initialize an LLMProvider instance.

        Args:
            name: Name of the LLM provider (e.g., "OpenAI")
            base_url: Base URL for the provider's API endpoint
            api_key: Optional API key for authentication
            models: Optional dictionary of pre-loaded models
        """
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.models = models if models is not None else {}
        self.headers = self._create_default_headers()
        LOG.debug(f"Initialized {self.name} provider with base URL: {self.base_url}")

    def _create_default_headers(self) -> Dict[str, str]:
        """
        Create default HTTP headers for API requests, including authentication.

        Handles provider-specific authentication schemes (Bearer tokens,
        custom headers, etc.) based on the provider name.

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json"  # Standard for JSON APIs
        }

        # Add authentication if API key is provided
        if self.api_key:
            # OpenAI-style Bearer token authentication
            if self.name.lower() in ["openai", "azure openai", "anthropic"]:
                headers["Authorization"] = f"Bearer {self.api_key}"
                logging.debug(f"Added Bearer token authentication for {self.name}")
            # Google-style API key header
            elif self.name.lower() in ["google", "gemini"]:
                headers["x-goog-api-key"] = self.api_key
                LOG.debug(f"Added x-goog-api-key authentication for {self.name}")

        return headers

    def add_model(self,
                 model_name: str,
                 model_type: str,
                 model_path: str,
                 input_price: float,
                 output_price: float,
                 max_input_tokens: int,
                 max_output_tokens: int,
                 context_window: int,
                 description: Optional[str] = None) -> None:
        """
        Add a single model to the provider's model library.

        Args:
            model_name: Common name for the model
            model_type: Classification (e.g., 'chat', 'embedding')
            model_path: Provider-specific identifier
            input_price: Cost per million input tokens (USD)
            output_price: Cost per million output tokens (USD)
            max_input_tokens: Maximum input tokens allowed
            max_output_tokens: Maximum output tokens allowed
            context_window: Total token capacity
            description: Optional model description
        """
        key = f"{self.name}:{model_name}"
        self.models[key] = ModelInfo(
            provider_name=self.name,
            model_name=model_name,
            model_type=model_type,
            model_path=model_path,
            input_price=input_price,
            output_price=output_price,
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
            context_window=context_window,
            description=description
        )
        LOG.debug(f"Added model '{key}' to {self.name} provider")

    def add_models_from_dict(self, models_dict: List[Dict]) -> None:
        """
        Bulk add multiple models from a list of dictionaries.

        Args:
            models_dict: List of model data dictionaries, each containing
                         all required ModelInfo fields
        """
        for model_data in models_dict:
            self.add_model(
                model_name=model_data["model_name"],
                model_type=model_data["model_type"],
                model_path=model_data["model_path"],
                input_price=model_data["input_price"],
                output_price=model_data["output_price"],
                max_input_tokens=model_data["max_input_tokens"],
                max_output_tokens=model_data["max_output_tokens"],
                context_window=model_data["context_window"],
                description=model_data.get("description")
            )
        LOG.info(f"Added {len(models_dict)} models to {self.name} provider")

    def remove_model(self, model_name: str) -> None:
        """
        Remove a model from the provider's library.

        Args:
            model_name: Name of the model to remove
        """
        key = f"{self.name}:{model_name}"
        if key in self.models:
            del self.models[key]
            LOG.debug(f"Removed model '{key}' from {self.name} provider")
        else:
            LOG.warning(f"Attempted to remove non-existent model '{key}' from {self.name} provider")

    def get_available_models(self) -> List[str]:
        """
        Get sorted list of available model names.

        Returns:
            Sorted list of model names
        """
        return sorted([info.model_name for info in self.models.values()])

    def get_model_info(self, provider_name: str, model_name_or_path: str) -> Optional[ModelInfo]:
        """
        Get detailed information about a specific model.

        Args:
            provider_name: Name of the provider (used for logging and key construction)
            model_name: Name of the model to retrieve info for

        Returns:
            ModelInfo object if found, None otherwise
        """
        key = f"{provider_name}:{model_name_or_path}"
        info = self.models.get(key)
        if info is None:
            for key in self.models:
                if self.models[key].model_path == model_name_or_path:
                    info = self.models[key]

        if info:
            LOG.debug(f"Retrieved info for model '{key}' from {provider_name} provider")
        else:
            LOG.debug(f"Model '{key}' not found in {provider_name} provider")
        return info

    def get_models_by_type(self, model_type: str) -> List[str]:
        """
        Filter models by their type/classification.

        Args:
            model_type: Type to filter by (e.g., 'chat')

        Returns:
            List of model names matching the specified type
        """
        models = [info.model_name for info in self.models.values() if info.model_type == model_type]
        LOG.debug(f"Found {len(models)} {model_type} models in {self.name} provider")
        return models

    def get_models_by_context_window(self, min_tokens: int) -> List[str]:
        """
        Filter models by minimum context window size.

        Args:
            min_tokens: Minimum required context window size

        Returns:
            List of model names meeting the requirement
        """
        models = [info.model_name for info in self.models.values() \
            if info.context_window >= min_tokens]
        LOG.debug(f"Found {len(models)} models in {self.name} provider with context window \
            >= {min_tokens}")
        return models

    def calculate_estimated_cost(
        self, model_name: str, input_tokens: int, output_tokens: int) -> Optional[float]:
        """
        Calculate estimated cost for a request in USD.

        Args:
            model_name: Name of the model to use
            input_tokens: Estimated number of input tokens
            output_tokens: Estimated number of output tokens

        Returns:
            Estimated cost in USD, or None if model not found
        """
        model = self.get_model_info(self.name, model_name)
        if not model:
            LOG.warning(f"Could not calculate cost for unknown model '{model_name}'")
            return None

        # Calculate cost using per-million rates
        input_cost = (input_tokens / 1_000_000) * model.input_price
        output_cost = (output_tokens / 1_000_000) * model.output_price
        total_cost = round(input_cost + output_cost, 6)

        LOG.debug(
            f"Calculated cost for {model_name}: {input_tokens} input tokens + {output_tokens} \
                output tokens = ${total_cost}"
        )
        return total_cost

    def get_all_model_types(self) -> Set[str]:
        """
        Get all unique model types offered by this provider.

        Returns:
            Set of model type strings
        """
        types = {info.model_type for info in self.models.values()}
        LOG.debug(f"Found {len(types)} model types in {self.name} provider")
        return types

    def set_api_key(self, api_key: str) -> None:
        """
        Update API key and regenerate authentication headers.

        Args:
            api_key: New API key to use
        """
        self.api_key = api_key
        self.headers = self._create_default_headers()
        LOG.info(f"Updated API key for {self.name} provider")

    def has_model(self, model_name: str) -> bool:
        """
        Check if a model exists in the provider's library.

        Args:
            model_name: Name of the model to check

        Returns:
            True if model exists, False otherwise
        """
        key = f"{self.name}:{model_name}"
        exists = key in self.models
        LOG.debug(
            f"Model '{key}' {'exists' if exists else 'does not exist'} in {self.name} provider")
        return exists

    def __str__(self) -> str:
        """String representation of the provider."""
        return f"{self.name} LLM Provider (Base URL: {self.base_url}, Models: {len(self.models)})"

    def __repr__(self) -> str:
        """Official string representation for debugging."""
        return f"LLMProvider(name='{self.name}', base_url='{self.base_url}', \
                models={[info.model_name for info in self.models.values()]})"


class LLMFactory:
    """
    Factory class for managing multiple LLM providers from a unified configuration.

    Provides centralized access to multiple LLM providers, enabling cross-provider
    model discovery, comparison, and management.
    """

    def __init__(self):
        """Initialize an empty LLMFactory."""
        # Dictionary to store providers by name for quick lookup
        self.providers: Dict[str, LLMProvider] = {}
        LOG.debug("Initialized empty LLMFactory")
        self.load_provider_from_file(os.path.join(CURR_DIR, "llm_config.json"))

    def load_provider_from_file(
        self, file_path: str, api_keys: Optional[Dict[str, str]] = None) -> None:
        """
        Load multiple LLM providers from a unified JSON configuration file.

        Args:
            file_path: Path to the JSON configuration file
            api_keys: Optional dict mapping provider names to their API keys
                      (more secure than storing in config file)
        """
        # Default to empty dict if no API keys provided
        api_keys = api_keys or {}

        try:
            # Validate file existence and type
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Configuration file not found: {file_path}")

            if not os.path.isfile(file_path):
                raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")

            # Read and parse the configuration file
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            LOG.debug(f"Successfully parsed configuration file: {file_path}")

            # Validate configuration structure
            if "providers" not in config:
                raise ValueError("Configuration file must contain a 'providers' array")

            # Create and store each provider from configuration
            for provider_data in config["providers"]:
                provider_name = provider_data["provider_name"]
                # Get API key for this provider if available
                api_key = api_keys.get(provider_name)
                api_key_env = provider_data.get('api_key_env')

                if api_key is None and api_key_env is not None:
                    LOG.info(f"Get API key from os enviroment {api_key_env}")
                    api_key = os.environ.get(api_key_env)
                if api_key is None:
                    LOG.warning(f"API key for provider {provider_name} is None.")

                # Create provider instance
                provider = LLMProvider(
                    name=provider_name,
                    base_url=provider_data["base_url"],
                    api_key=api_key
                )

                # Add all models for this provider
                provider.add_models_from_dict(provider_data["models"])

                # Store provider in factory
                self.providers[provider_name] = provider
                LOG.info(f"Added {provider_name} provider to factory")

            LOG.info(f"Successfully loaded {len(self.providers)} providers from {file_path}")

        except Exception as e:
            LOG.error(f"Error loading providers from file: {str(e)}", exc_info=True)
            raise  # Re-raise to allow caller to handle if needed

    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """
        Retrieve a specific provider by name.

        Args:
            provider_name: Name of the provider to retrieve

        Returns:
            LLMProvider instance if found, None otherwise
        """
        provider = self.providers.get(provider_name)
        if provider:
            LOG.debug(f"Retrieved {provider_name} provider from factory")
        else:
            LOG.warning(f"Provider '{provider_name}' not found in factory")
        return provider

    def get_all_providers(self) -> List[LLMProvider]:
        """
        Get list of all registered providers.

        Returns:
            List of LLMProvider instances
        """
        providers = list(self.providers.values())
        LOG.debug(f"Retrieved {len(providers)} providers from factory")
        return providers

    def get_provider_names(self) -> List[str]:
        """
        Get sorted list of all provider names.

        Returns:
            Sorted list of provider names
        """
        names = sorted(self.providers.keys())
        LOG.debug(f"Retrieved names of {len(names)} providers")
        return names

    def get_all_models(self) -> Dict[str, Tuple[str, ModelInfo]]:
        """
        Get all models across all providers with their provider information.

        Returns:
            Dictionary mapping model keys (provider_name:model_name) to
            tuples of (provider name, ModelInfo)
        """
        all_models = {}
        for provider_name, provider in self.providers.items():
            for key, model_info in provider.models.items():
                all_models[key] = (provider_name, model_info)
        LOG.debug(f"Retrieved information for {len(all_models)} models across all providers")
        return all_models

    def get_models_by_type(self, model_type: str) -> Dict[str, Tuple[str, ModelInfo]]:
        """
        Get all models of a specific type across all providers.

        Args:
            model_type: Type of models to retrieve (e.g., 'chat')

        Returns:
            Dictionary of matching models with their provider information
        """
        all_models = self.get_all_models()
        filtered = {
            name: (provider, info) for name, (provider, info) in all_models.items()
            if info.model_type == model_type
        }
        LOG.debug(f"Found {len(filtered)} {model_type} models across all providers")
        return filtered

    def llm(self, provider_name: str, model_name: str, temperature: float = 0.7,
            max_tokens: Optional[int] = None, **kwargs: Any) -> Optional[CustomLLMChat]:
        """
        Create a CustomLLMChat instance for the specified model.

        Args:
            provider_name: Name of the provider (used to retrieve provider and for instance_id)
            model_name: Name or path of the model to initialize
            temperature: Sampling temperature (0 = deterministic, 2 = creative)
            max_tokens: Maximum number of tokens to generate in responses
            **kwargs: Additional arguments passed to CustomLLMChat

        Returns:
            CustomLLMChat instance if model exists, None otherwise
        """
        provider = self.get_provider(provider_name)
        if not provider:
            LOG.warning(f"Cannot create CustomLLMChat: Provider '{provider_name}' not found")
            return None

        model_info = provider.get_model_info(provider_name, model_name)
        if not model_info:
            LOG.warning(f"Cannot create CustomLLMChat: Model '{model_name}' not found \
                in {provider_name} provider")
            return None

        # Use model_path for API calls, as it may differ from model_name
        instance_id = f"{provider_name}:{model_name}-{int(time.time())}"
        llm_instance = CustomLLMChat(
            model=model_info.model_path,
            api_key=provider.api_key,
            base_url=provider.base_url,
            temperature=temperature,
            max_tokens=max_tokens if max_tokens is not None else model_info.max_output_tokens,
            instance_id=instance_id,
            **kwargs
        )
        LOG.debug(f"Created CustomLLMChat instance '{instance_id}' for model '{model_name}' \
            in {provider_name} provider")
        return llm_instance

    def __str__(self) -> str:
        """String representation of the factory."""
        total_models = sum(len(p.models) for p in self.providers.values())
        return f"LLMFactory (Providers: {len(self.providers)}, Total Models: {total_models})"


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Set logging level to INFO for the example
    logging.getLogger().setLevel(logging.INFO)

    # Save configuration to a temporary file
    config_file = "llm_config.json"

    # API keys would typically come from environment variables in production
    api_keys = {
        "OpenAI": "your-openai-api-key",
        "Anthropic": "your-anthropic-api-key"
    }

    # Initialize factory and load providers
    llm_factory = LLMFactory()

    # Demonstrate factory capabilities
    logging.info(f"Factory status: {llm_factory}")
    logging.info(f"Available providers: {llm_factory.get_provider_names()}")

    # Work with OpenAI provider
    openai = llm_factory.get_provider("OpenAI")
    if openai:
        logging.info(f"OpenAI models: {openai.get_available_models()}")
        gpt4_cost = openai.calculate_estimated_cost("GPT-4", 10000, 2000)
        logging.info(f"Estimated cost for GPT-4 (10k input/2k output): ${gpt4_cost}")

    # Work with Anthropic provider
    anthropic = llm_factory.get_provider("Anthropic")
    if anthropic:
        logging.info(f"Anthropic models: {anthropic.get_available_models()}")
        claude_cost = anthropic.calculate_estimated_cost("Claude Opus", 10000, 2000)
        logging.info(f"Estimated cost for Claude Opus (10k input/2k output): ${claude_cost}")

    # Cross-provider model discovery
    chat_models = llm_factory.get_models_by_type("chat")
    logging.info("\nAll chat models across providers:")
    for model_key, (provider_name, info) in chat_models.items():
        logging.info(
            f"- {info.model_name} (from {provider_name}): {info.context_window} token context")

    llm_instance = llm_factory.llm("dashscope", "qwen-turbo")
    if llm_instance:
        print("Successfully created LLM instance")
        resp = llm_instance.invoke("hello who are you?")
        resp = llm_instance.invoke("i love you?")
        print(llm_instance.get_logs())
