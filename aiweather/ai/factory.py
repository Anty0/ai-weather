"""Provider construction and availability probing for AI Weather."""

import asyncio
from collections.abc import Callable

import structlog

from ..config import Settings
from .base import AIProvider
from .ollama import OllamaProvider

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

ProviderFactory = Callable[[Settings], dict[str, AIProvider]]

_PROVIDER_BUILDERS: dict[str, Callable[[Settings], AIProvider]] = {
    "ollama": lambda settings: OllamaProvider(settings.ollama),
}


def default_provider_factory(settings: Settings) -> dict[str, AIProvider]:
    """Build one provider instance per provider name referenced by enabled models.

    An enabled model referencing an unknown provider is skipped with a warning rather
    than aborting startup; AIManager renders a per-model error visualization for it, so
    one misconfigured model never takes down the whole app.
    """
    providers: dict[str, AIProvider] = {}
    for model in settings.ai_models:
        if not model.enabled or model.provider in providers:
            continue
        builder = _PROVIDER_BUILDERS.get(model.provider)
        if builder is None:
            logger.warning("unknown_provider", provider=model.provider, model=model.name)
            continue
        providers[model.provider] = builder(settings)
    return providers


async def probe_all(providers: dict[str, AIProvider], timeout: float) -> dict[str, bool]:
    """Probe every provider's availability under the given per-probe timeout."""
    names = list(providers)
    results = await asyncio.gather(*(probe_available(providers[name], timeout) for name in names))
    return dict(zip(names, results))


async def probe_available(provider: AIProvider, timeout: float) -> bool:
    """Check provider availability under a hard timeout; any failure means not-ready."""
    try:
        return await asyncio.wait_for(provider.is_available(), timeout)
    except Exception as e:
        logger.debug("provider_probe_failed", error=str(e))
        return False
