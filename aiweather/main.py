"""Main FastAPI application for AI Weather."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings
from .scheduler import WeatherScheduler
from .state import StateService
from .storage import ArchiveManager
from .websocket import ConnectionManager

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

# Global state
manager: ConnectionManager
scheduler: WeatherScheduler
archive: ArchiveManager
settings: Settings
state_service: StateService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown logic."""
    global scheduler, archive, settings, manager, state_service

    settings = load_settings()
    logger.info("config_loaded")
    archive = ArchiveManager(settings.storage.data_dir)

    # Initialize state service and load from the archive
    state_service = StateService(archive, settings)
    try:
        await state_service.load_from_archive()
    except Exception as e:
        logger.error("archive_load_failed", error=str(e))

    manager = ConnectionManager(settings, state_service)
    scheduler = WeatherScheduler(settings, archive, state_service, manager)

    await scheduler.start()

    logger.info("application_started")

    yield

    # Shutdown
    await scheduler.stop()
    logger.info("application_stopped")


app = FastAPI(title="AI Weather", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_root() -> FileResponse:
    """Serve the main page."""
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates (server-push only)."""
    await manager.handle(websocket)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
