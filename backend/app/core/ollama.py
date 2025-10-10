"""
Ollama Integration for Local LLM Services

This module provides a client for interacting with Ollama's local LLM server.
Supports summarization, tagging, and other AI features.
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
import httpx

from .config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama local LLM server"""

    def __init__(self, base_url: str = None, timeout: int = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.timeout = timeout or settings.OLLAMA_REQUEST_TIMEOUT
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def list_models(self) -> List[Dict]:
        """List available models"""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def check_model(self, model_name: str) -> bool:
        """Check if a model is available"""
        models = await self.list_models()
        return any(model["name"] == model_name for model in models)

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from the registry"""
        try:
            logger.info(f"Pulling Ollama model: {model_name}")
            response = await self.client.post(
                "/api/pull",
                json={"name": model_name},
                timeout=1800  # 30 minutes for large models
            )
            response.raise_for_status()

            # Stream the pull progress
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "status" in data:
                            logger.info(f"Pull progress: {data['status']}")
                    except json.JSONDecodeError:
                        continue

            return True
        except Exception as e:
            logger.error(f"Failed to pull Ollama model {model_name}: {e}")
            return False

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str = None,
        template: str = None,
        context: List[int] = None,
        stream: bool = False,
        raw: bool = False,
        format: str = None,
        options: Dict[str, Any] = None
    ) -> Union[str, Dict]:
        """
        Generate text using Ollama model

        Args:
            model: Model name
            prompt: Input prompt
            system: System message
            template: Template to use
            context: Context from previous conversation
            stream: Whether to stream the response
            raw: Return raw response
            format: Response format (json, etc.)
            options: Additional model options

        Returns:
            Generated text or full response dict
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }

        if system:
            payload["system"] = system
        if template:
            payload["template"] = template
        if context:
            payload["context"] = context
        if format:
            payload["format"] = format
        if options:
            payload["options"] = options

        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()

            if stream:
                # For streaming, we'd need to handle the stream
                # For now, return the full response
                return response.json()
            else:
                data = response.json()
                if raw:
                    return data
                return data.get("response", "")

        except Exception as e:
            logger.error(f"Failed to generate with Ollama: {e}")
            raise

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        format: str = None,
        options: Dict[str, Any] = None
    ) -> Union[str, Dict]:
        """
        Chat completion using Ollama model

        Args:
            model: Model name
            messages: List of messages with role/content
            stream: Whether to stream the response
            format: Response format
            options: Additional model options

        Returns:
            Generated response
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }

        if format:
            payload["format"] = format
        if options:
            payload["options"] = options

        try:
            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()
            if stream:
                return data
            else:
                # Extract the last message content
                if "message" in data:
                    return data["message"].get("content", "")
                return ""

        except Exception as e:
            logger.error(f"Failed to chat with Ollama: {e}")
            raise


# Global client instance
ollama_client = OllamaClient()


async def ensure_model_available(model_name: str) -> bool:
    """Ensure a model is available, pulling it if necessary"""
    async with OllamaClient() as client:
        if await client.check_model(model_name):
            logger.info(f"Model {model_name} is already available")
            return True

        logger.info(f"Model {model_name} not found, attempting to pull...")
        success = await client.pull_model(model_name)
        if success:
            logger.info(f"Successfully pulled model {model_name}")
            return True
        else:
            logger.error(f"Failed to pull model {model_name}")
            return False


# Convenience functions for common operations
async def summarize_text(text: str, model: str = None) -> str:
    """Summarize text using Ollama"""
    model = model or settings.OLLAMA_MODEL_SUMMARIZATION

    # Ensure model is available
    if not await ensure_model_available(model):
        raise ValueError(f"Model {model} is not available")

    system_prompt = """You are a legal document summarizer. Create concise, accurate summaries of legal documents, contracts, and case materials. Focus on key facts, parties involved, legal issues, and outcomes. Keep summaries objective and factual."""

    prompt = f"""Please summarize the following legal document:

{text[:8000]}  # Limit input size

Summary:"""

    async with OllamaClient() as client:
        return await client.generate(
            model=model,
            prompt=prompt,
            system=system_prompt
        )


async def tag_document(text: str, model: str = None) -> List[str]:
    """Auto-tag document using Ollama"""
    model = model or settings.OLLAMA_MODEL_TAGGING

    # Ensure model is available
    if not await ensure_model_available(model):
        raise ValueError(f"Model {model} is not available")

    system_prompt = """You are a legal document classifier. Analyze documents and provide relevant tags from this taxonomy:
- contract, agreement, settlement
- lawsuit, litigation, complaint, defense
- court_order, judgment, ruling
- statute, regulation, law
- evidence, testimony, deposition
- property, real_estate, title
- employment, labor, hr
- intellectual_property, patent, trademark, copyright
- corporate, merger, acquisition
- bankruptcy, insolvency
- family_law, divorce, custody
- criminal, prosecution, defense

Return only a comma-separated list of the most relevant tags."""

    prompt = f"""Analyze this document and provide the most relevant tags:

{text[:4000]}

Tags:"""

    async with OllamaClient() as client:
        response = await client.generate(
            model=model,
            prompt=prompt,
            system=system_prompt
        )

        # Parse comma-separated tags
        tags = [tag.strip() for tag in response.split(',') if tag.strip()]
        return tags[:10]  # Limit to 10 tags


async def extract_entities(text: str, model: str = None) -> Dict[str, List[str]]:
    """Extract structured entities using Ollama"""
    model = model or settings.OLLAMA_MODEL_SUMMARIZATION

    # Ensure model is available
    if not await ensure_model_available(model):
        raise ValueError(f"Model {model} is not available")

    system_prompt = """You are a legal entity extractor. Extract structured information from legal documents. Return JSON with these categories:
- parties: People and organizations mentioned
- dates: Important dates (filings, hearings, deadlines)
- amounts: Monetary amounts and values
- citations: Legal citations (cases, statutes)
- locations: Court locations, addresses

Return only valid JSON."""

    prompt = f"""Extract entities from this legal document:

{text[:4000]}

Return JSON:"""

    async with OllamaClient() as client:
        response = await client.generate(
            model=model,
            prompt=prompt,
            system=system_prompt,
            format="json"
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse entity extraction JSON, returning empty dict")
            return {}