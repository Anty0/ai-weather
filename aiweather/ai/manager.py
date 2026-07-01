"""AI manager for orchestrating multiple AI models with progressive updates."""

import asyncio
import html as html_lib
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from string import Template
from typing import Any

import structlog

from ..config import AIModelConfig, Settings
from ..paths import ERROR_TEMPLATE
from ..visualization import HtmlNormalizer, Visualization
from .base import AIProvider

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

OnUpdate = Callable[[str, Visualization, bool], Awaitable[Any]]


class AIManager:
    """Orchestrates AI model requests with progressive updates."""

    def __init__(
        self,
        settings: Settings,
        providers: dict[str, AIProvider],
        normalizer: HtmlNormalizer | None = None,
    ) -> None:
        """Initialize AI manager.

        Args:
            settings: Application settings
            providers: Mapping of provider name to provider instance
            normalizer: Shared HTML normalizer (created if not provided)
        """
        self.settings = settings
        self.providers = providers
        self.normalizer = normalizer or HtmlNormalizer()
        self._error_template = Template(ERROR_TEMPLATE.read_text())

    async def generate_all(
        self,
        weather_json: str,
        on_update: OnUpdate | None = None,
    ) -> dict[str, Visualization]:
        """Generate visualizations from all enabled AI models with progressive callbacks.

        Args:
            weather_json: Raw JSON string of weather data from API
            on_update: Optional async callback invoked as each model streams and completes.
                Signature: async def callback(model_name, visualization, is_complete)

        Returns:
            Dictionary mapping model names to their Visualization
        """
        try:
            weather_obj = json.loads(weather_json)
            weather_json_formatted = json.dumps(weather_obj, indent=2)
        except json.JSONDecodeError:
            logger.warning("json_parse_failed", using_raw=True)
            weather_json_formatted = weather_json

        prompt = self.settings.prompt.template.replace("{weather_json}", weather_json_formatted)
        interval = self.settings.ai.progress_interval_seconds

        async def generate_one(model_name: str, model_config: AIModelConfig) -> tuple[str, Visualization]:
            try:
                provider = self.providers.get(model_config.provider)
                if provider is None:
                    raise ValueError(f"Provider {model_config.provider!r} not found")

                last_update = datetime.now()

                async def on_chunk(accumulated_html: str) -> None:
                    nonlocal last_update
                    if on_update and (datetime.now() - last_update).total_seconds() >= interval:
                        last_update = datetime.now()
                        await on_update(model_name, Visualization.from_raw(accumulated_html, self.normalizer), False)

                raw = await asyncio.wait_for(
                    provider.generate_html(
                        prompt=prompt,
                        model_id=model_config.model_id,
                        on_chunk=on_chunk if on_update else None,
                        temperature=model_config.temperature,
                    ),
                    timeout=model_config.timeout,
                )

                visualization = Visualization.from_raw(raw, self.normalizer)
                if on_update:
                    await on_update(model_name, visualization, True)
                return model_name, visualization

            except Exception as e:
                logger.error("model_failed", model=model_name, error=str(e))
                visualization = Visualization.from_raw(self._error_html(model_name, str(e)), self.normalizer)
                if on_update:
                    await on_update(model_name, visualization, True)
                return model_name, visualization

        generate_fn: Callable[[str, AIModelConfig], Awaitable[tuple[str, Visualization]]]

        max_concurrent = self.settings.ai.max_concurrent
        if max_concurrent > 0:
            semaphore = asyncio.Semaphore(max_concurrent)

            async def generate_limited(name: str, cfg: AIModelConfig) -> tuple[str, Visualization]:
                async with semaphore:
                    return await generate_one(name, cfg)

            generate_fn = generate_limited
        else:
            generate_fn = generate_one

        tasks = [generate_fn(m.name, m) for m in self.settings.ai_models if m.enabled]
        results = await asyncio.gather(*tasks)
        return dict(results)

    def _error_html(self, model_name: str, error: str) -> str:
        """Render the error page for a failed generation with HTML-escaped values."""
        return self._error_template.substitute(
            model_name=html_lib.escape(model_name),
            error=html_lib.escape(error),
        )
