"""Main FastAPI application for AI Weather."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .ai import AIManager, ProviderFactory, default_provider_factory, probe_all
from .config import Settings, load_settings
from .paths import INDEX_HTML, STATIC_DIR
from .scheduler import RefreshService, WeatherScheduler
from .state import StateService
from .storage import ArchiveManager
from .visualization import HtmlNormalizer
from .weather import WeatherClient
from .websocket import ConnectionManager

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


def create_app(*, settings: Settings | None = None, provider_factory: ProviderFactory | None = None) -> FastAPI:
    """Build the FastAPI app.

    Args:
        settings: Injected settings; when omitted, loaded from config at startup.
        provider_factory: Injected provider factory; defaults to the Ollama factory.
    """
    app = FastAPI(title="AI Weather", lifespan=lifespan)
    app.state.settings = settings
    app.state.provider_factory = provider_factory or default_provider_factory
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def read_root() -> FileResponse:
        """Serve the main page."""
        return FileResponse(INDEX_HTML)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time updates (server-push only)."""
        await websocket.app.state.ws_manager.handle(websocket)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Cheap liveness check with no external I/O."""
        return {"status": "ok"}

    @app.get("/ready")
    async def readiness_check(request: Request, response: Response) -> dict[str, Any]:
        """Readiness check that probes provider availability under a bounded timeout."""
        settings = request.app.state.settings
        providers = request.app.state.providers
        availability = await probe_all(providers, settings.ai.readiness_probe_timeout_seconds)
        ready = bool(availability) and all(availability.values())
        if not ready:
            response.status_code = 503
        return {"ready": ready, "providers": availability}

    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Construct all components, wire them onto app.state, and manage the scheduler lifecycle."""
    settings: Settings = app.state.settings or load_settings()
    provider_factory: ProviderFactory = app.state.provider_factory
    app.state.settings = settings
    logger.info("config_loaded")

    normalizer = HtmlNormalizer()
    archive = ArchiveManager(settings.storage.data_dir)
    state_service = StateService()
    providers = provider_factory(settings)
    ai_manager = AIManager(settings, providers, normalizer)
    ws_manager = ConnectionManager(settings, state_service)
    weather_client = WeatherClient(settings.weather)
    refresh_service = RefreshService(
        settings, weather_client, ai_manager, archive, state_service, ws_manager, normalizer
    )
    scheduler = WeatherScheduler(settings, refresh_service)

    app.state.archive = archive
    app.state.state_service = state_service
    app.state.providers = providers
    app.state.ai_manager = ai_manager
    app.state.ws_manager = ws_manager
    app.state.refresh_service = refresh_service
    app.state.scheduler = scheduler

    try:
        await refresh_service.load_initial_state()
    except Exception as e:
        logger.error("archive_load_failed", error=str(e))

    availability = await probe_all(providers, settings.ai.readiness_probe_timeout_seconds)
    logger.info("provider_availability", availability=availability)

    await scheduler.start()
    logger.info("application_started")

    yield

    await scheduler.stop()
    logger.info("application_stopped")


app = create_app()
