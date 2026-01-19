"""Ollama AI provider implementation."""

from collections.abc import Awaitable, Callable

import ollama
import structlog

from ..config import OllamaConfig
from .base import AIProvider

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class OllamaProvider(AIProvider):
    """Ollama AI provider implementation."""

    def __init__(self, config: OllamaConfig) -> None:
        """Initialize Ollama provider.

        Args:
            config: Ollama configuration
        """
        self.config = config
        self.client = ollama.AsyncClient(host=config.base_url, timeout=config.timeout)
        logger.info("ollama_initialized", base_url=config.base_url, timeout=config.timeout)

    async def generate_html(
        self,
        prompt: str,
        model_id: str,
        on_chunk: Callable[[str], Awaitable[None]] | None = None,
        **kwargs: object,
    ) -> str:
        """Generate HTML using an Ollama model with streaming support.

        Args:
            prompt: The prompt to send to the model
            model_id: Ollama model identifier
            on_chunk: Optional callback invoked with accumulated HTML as chunks arrive
            **kwargs: Additional arguments (temperature, etc.)

        Returns:
            Generated HTML content

        Raises:
            Exception: If generation fails
        """
        try:
            response = await self.client.generate(
                model=model_id,
                prompt=prompt,
                options={"temperature": kwargs.get("temperature", 0.7)},
                stream=True,
                keep_alive="2h",
            )

            accumulated = ""
            async for chunk in response:
                text = chunk.get("response", "")
                if text:
                    accumulated += text
                    if on_chunk:
                        await on_chunk(accumulated)

            logger.info("html_generated", model=model_id, length=len(accumulated))
            return accumulated

        except Exception as e:
            logger.error("html_generation_failed", model=model_id, error=str(e))
            raise

    async def is_available(self) -> bool:
        """Check if Ollama is running and accessible.

        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            await self.client.list()
            return True
        except Exception as e:
            logger.debug("ollama_unavailable", error=str(e))
            return False
