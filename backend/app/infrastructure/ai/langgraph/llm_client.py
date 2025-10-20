"""
LLM Client for LangGraph Agents

Provides LangChain-compatible Ollama client for use in LangGraph workflows.
Wraps the existing Ollama client with LangChain's BaseChatModel interface.
"""

import logging
from typing import Optional, List, Dict, Any, AsyncIterator
from langchain_community.chat_models import ChatOllama
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from app.core.config import settings
from app.core.ollama import OllamaClient, ensure_model_available

logger = logging.getLogger(__name__)


class LangGraphOllamaClient:
    """
    Ollama client wrapper for LangGraph agents.

    This class provides a unified interface for both LangChain's ChatOllama
    (for ReAct agents and structured tool use) and direct Ollama API access
    (for custom agent implementations).
    """

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: int = 300,
    ):
        """
        Initialize the LangGraph Ollama client.

        Args:
            model: Ollama model name (e.g., "llama3.1:70b")
            base_url: Ollama server URL (defaults to settings.OLLAMA_BASE_URL)
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # Initialize LangChain ChatOllama for ReAct agents
        self._langchain_client = ChatOllama(
            base_url=self.base_url,
            model=model,
            temperature=temperature,
            num_predict=max_tokens,
            timeout=timeout,
        )

        # Initialize direct Ollama client for custom implementations
        self._ollama_client = OllamaClient(
            base_url=self.base_url,
            timeout=timeout,
        )

        logger.info(
            f"Initialized LangGraphOllamaClient: model={model}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )

    @property
    def langchain(self) -> BaseChatModel:
        """
        Get LangChain-compatible chat model.

        Use this for ReAct agents and LangChain tool integration.

        Returns:
            ChatOllama instance
        """
        return self._langchain_client

    async def ensure_model_ready(self) -> bool:
        """
        Ensure the model is available, pulling it if necessary.

        Returns:
            True if model is ready, False otherwise
        """
        try:
            return await ensure_model_available(self.model)
        except Exception as e:
            logger.error(f"Failed to ensure model {self.model} is ready: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        """
        Generate text using direct Ollama API.

        Args:
            prompt: Input prompt
            system: Optional system message
            format: Optional response format (e.g., "json")

        Returns:
            Generated text
        """
        try:
            response = await self._ollama_client.generate(
                model=self.model,
                prompt=prompt,
                system=system,
                format=format,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )
            return response
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        format: Optional[str] = None,
    ) -> str:
        """
        Chat completion using direct Ollama API.

        Args:
            messages: List of messages with role/content
            format: Optional response format (e.g., "json")

        Returns:
            Generated response
        """
        try:
            response = await self._ollama_client.chat(
                model=self.model,
                messages=messages,
                format=format,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )
            return response
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            raise

    async def close(self):
        """Close underlying HTTP clients."""
        await self._ollama_client.close()


# ==================== Client Factory Functions ====================

def get_ollama_llm(
    model: str,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    timeout: int = 300,
) -> BaseChatModel:
    """
    Get a LangChain-compatible Ollama LLM for use in agents.

    This is a simple factory function that returns a ChatOllama instance
    configured for LangGraph agents.

    Args:
        model: Ollama model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds

    Returns:
        ChatOllama instance compatible with LangChain

    Example:
        >>> llm = get_ollama_llm("llama3.1:70b", temperature=0.1)
        >>> from langchain.agents import create_react_agent
        >>> agent = create_react_agent(llm, tools, prompt)
    """
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=model,
        temperature=temperature,
        num_predict=max_tokens,
        timeout=timeout,
    )


def get_langgraph_client(
    model: str,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    timeout: int = 300,
) -> LangGraphOllamaClient:
    """
    Get a LangGraph Ollama client with both LangChain and direct API access.

    Use this when you need flexibility between LangChain's tool integration
    and direct API calls.

    Args:
        model: Ollama model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds

    Returns:
        LangGraphOllamaClient instance

    Example:
        >>> client = get_langgraph_client("llama3.1:70b")
        >>> # Use with LangChain tools
        >>> agent = create_react_agent(client.langchain, tools, prompt)
        >>> # Or use direct API
        >>> response = await client.generate("Summarize this document")
    """
    return LangGraphOllamaClient(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


# ==================== Model Selection Helpers ====================

def get_default_model() -> str:
    """
    Get the default Ollama model from settings.

    Returns:
        Default model name
    """
    return settings.OLLAMA_MODEL_SUMMARIZATION


def get_model_for_agent(agent_name: str) -> str:
    """
    Get the appropriate model for a specific agent.

    Args:
        agent_name: Agent name

    Returns:
        Model name for the agent

    Note:
        Currently returns the default model. Can be extended to support
        agent-specific model selection (e.g., larger models for synthesis).
    """
    # Could extend this to map specific agents to specific models
    # For now, use the configured default
    return settings.OLLAMA_MODEL_SUMMARIZATION


async def ensure_models_ready(models: List[str]) -> Dict[str, bool]:
    """
    Ensure multiple models are available.

    Args:
        models: List of model names

    Returns:
        Dictionary mapping model names to availability status
    """
    results = {}
    for model in models:
        try:
            results[model] = await ensure_model_available(model)
        except Exception as e:
            logger.error(f"Failed to check model {model}: {e}")
            results[model] = False
    return results


# ==================== Testing Utilities ====================

async def test_model_connection(model: str) -> bool:
    """
    Test if we can connect to Ollama and use a specific model.

    Args:
        model: Model name to test

    Returns:
        True if connection and model work, False otherwise
    """
    try:
        client = get_langgraph_client(model)
        await client.ensure_model_ready()

        # Test a simple generation
        response = await client.generate(
            prompt="Say 'OK' if you can read this.",
            system="You are a test assistant. Respond with just 'OK'.",
        )

        await client.close()

        return "ok" in response.lower()
    except Exception as e:
        logger.error(f"Model connection test failed for {model}: {e}")
        return False
