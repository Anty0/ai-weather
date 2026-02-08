"""AI manager for orchestrating multiple AI models with progressive updates."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional, Any, Awaitable

import structlog

from ..config import Settings, AIModelConfig
from .base import AIProvider
from .ollama import OllamaProvider

ERROR_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "static" / "templates" / "error.html"

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class AIManager:
    """Orchestrates AI model requests with progressive updates."""

    def __init__(self, settings: Settings) -> None:
        """Initialize AI manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.providers: Dict[str, AIProvider] = {}
        self._error_template = ERROR_TEMPLATE_PATH.read_text()

        # Initialize Ollama provider
        self.providers["ollama"] = OllamaProvider(settings.ollama)

    async def generate_all(
        self,
        weather_json: str,
        on_update: Optional[Callable[[str, str], Awaitable[Any]]] = None,
    ) -> Dict[str, str]:
        """Generate HTML from all enabled AI models with progressive callbacks.

        Args:
            weather_json: Raw JSON string of weather data from API
            on_update: Optional callback called when each model updates its output.
                        Signature: async def callback(model_name: str, html: str)

        Returns:
            Dictionary mapping model names to generated HTML
        """
        # Prepare prompt with pretty-printed JSON
        try:
            weather_obj = json.loads(weather_json)
            weather_json_formatted = json.dumps(weather_obj, indent=2)
        except json.JSONDecodeError:
            logger.warning("json_parse_failed", using_raw=True)
            weather_json_formatted = weather_json

        prompt = self.settings.prompt.template.format(weather_json=weather_json_formatted)

        async def generate_with_callback(model_name: str, model_config: AIModelConfig) -> tuple[str, str]:
            """Generate and call callback when done.

            Args:
                model_name: Name of the model
                model_config: Model configuration

            Returns:
                Tuple of (model_name, html)
            """
            try:
                # Type check to ensure model_config has the right attributes
                if not hasattr(model_config, "provider"):
                    raise AttributeError("model_config missing provider attribute")

                provider = self.providers.get(model_config.provider)
                if not provider:
                    raise Exception(f"Provider {model_config.provider} not found")

                last_update = datetime.now()

                # Create a model-specific chunk callback
                async def model_chunk_callback(accumulated_html: str) -> None:
                    nonlocal last_update
                    if on_update:
                        if (datetime.now() - last_update).seconds >= 5:
                            last_update = datetime.now()
                            await on_update(model_name, accumulated_html)

                html = await asyncio.wait_for(
                    provider.generate_html(
                        prompt=prompt,
                        model_id=model_config.model_id,
                        on_chunk=model_chunk_callback if on_update else None,
                        temperature=model_config.temperature,
                    ),
                    timeout=model_config.timeout,
                )

                # Call callback immediately when this model completes
                if on_update:
                    await on_update(model_name, html)

                return model_name, html

            except Exception as e:
                logger.error("model_failed", model=model_name, error=str(e))
                html = self._error_html(model_name, str(e))

                # Call callback even for errors
                if on_update:
                    await on_update(model_name, html)

                return model_name, html

        generate_fn: Callable[[str, AIModelConfig], Awaitable[tuple[str, str]]]

        max_concurrent = self.settings.ai.max_concurrent
        if max_concurrent > 0:
            # Limit concurrent requests
            semaphore = asyncio.Semaphore(max_concurrent)

            async def generate_limited(name: str, cfg: AIModelConfig) -> tuple[str, str]:
                async with semaphore:
                    return await generate_with_callback(name, cfg)

            generate_fn = generate_limited
        else:
            generate_fn = generate_with_callback

        tasks = [generate_fn(m.name, m) for m in self.settings.ai_models if m.enabled]
        results = await asyncio.gather(*tasks)

        # Return as dict
        return dict(results)

    def _error_html(self, model_name: str, error: str) -> str:
        """Generate error HTML for failed generations.

        Args:
            model_name: Name of the model that failed
            error: Error message

        Returns:
            HTML error page
        """
        return self._error_template.format(model_name=model_name, error=error)
