"""
Ollama client configuration and utilities for LangGraph agents.

This module provides utilities for creating and configuring Ollama LLM
instances for use in LangGraph agents.
"""

import logging
from typing import Optional
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOllama

logger = logging.getLogger(__name__)

# Default Ollama configuration
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:70b"
DEFAULT_TEMPERATURE = 0.1


def get_ollama_llm(
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    **kwargs,
) -> Ollama:
    """
    Get an Ollama LLM instance.

    Args:
        model: Model name (e.g., "llama3.1:70b", "mistral:latest")
        temperature: Temperature for generation (0.0-1.0)
        base_url: Ollama server URL
        **kwargs: Additional parameters for Ollama

    Returns:
        Configured Ollama LLM instance

    Example:
        >>> llm = get_ollama_llm(model="llama3.1:70b", temperature=0.1)
        >>> result = llm.invoke("What is 2+2?")
    """
    logger.info(f"Creating Ollama LLM with model={model}, temperature={temperature}")

    return Ollama(
        model=model,
        temperature=temperature,
        base_url=base_url,
        **kwargs,
    )


def get_ollama_chat_model(
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    **kwargs,
) -> ChatOllama:
    """
    Get an Ollama chat model instance.

    Chat models support structured message formats (system, user, assistant)
    and are preferred for conversational agents.

    Args:
        model: Model name (e.g., "llama3.1:70b", "mistral:latest")
        temperature: Temperature for generation (0.0-1.0)
        base_url: Ollama server URL
        **kwargs: Additional parameters for ChatOllama

    Returns:
        Configured ChatOllama instance

    Example:
        >>> chat = get_ollama_chat_model(model="llama3.1:70b")
        >>> from langchain_core.messages import HumanMessage
        >>> result = chat.invoke([HumanMessage(content="Hello!")])
    """
    logger.info(f"Creating Ollama chat model with model={model}, temperature={temperature}")

    return ChatOllama(
        model=model,
        temperature=temperature,
        base_url=base_url,
        **kwargs,
    )


def get_agent_llm(
    agent_type: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> ChatOllama:
    """
    Get LLM configured for a specific agent type.

    Different agents may benefit from different configurations:
    - Discovery, Planner: Lower temperature for consistency
    - Analysts: Moderate temperature for creativity
    - Synthesis: Higher temperature for natural language

    Args:
        agent_type: Type of agent (discovery, planner, analyst, synthesis)
        model: Override default model
        temperature: Override default temperature

    Returns:
        Configured ChatOllama instance

    Example:
        >>> llm = get_agent_llm("discovery")
        >>> llm = get_agent_llm("synthesis", temperature=0.3)
    """
    # Agent-specific defaults
    agent_configs = {
        "discovery": {"temperature": 0.05},
        "planner": {"temperature": 0.1},
        "document_analyst": {"temperature": 0.1},
        "transcript_analyst": {"temperature": 0.1},
        "communications_analyst": {"temperature": 0.1},
        "correlator": {"temperature": 0.15},
        "synthesis": {"temperature": 0.2},
    }

    config = agent_configs.get(agent_type.lower(), {})

    final_model = model or DEFAULT_MODEL
    final_temperature = temperature if temperature is not None else config.get("temperature", DEFAULT_TEMPERATURE)

    logger.info(f"Creating LLM for {agent_type} agent: model={final_model}, temperature={final_temperature}")

    return get_ollama_chat_model(
        model=final_model,
        temperature=final_temperature,
    )
