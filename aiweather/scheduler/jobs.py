from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..ai import AIManager
from ..config import Settings
from ..state import StateService
from ..storage import ArchiveManager
from ..weather import WeatherClient
from ..websocket import ConnectionManager

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class WeatherScheduler:
    """Manages scheduled weather fetching and AI generation."""

    def __init__(
        self,
        settings: Settings,
        archive: ArchiveManager,
        state_service: StateService,
        ws_manager: ConnectionManager,
    ) -> None:
        """Initialize scheduler.

        Args:
            settings: Application settings
            archive: Archive manager
            state_service: State service for managing current state
            ws_manager: WebSocket connection manager
        """
        self.settings = settings
        self.archive = archive
        self.state_service = state_service
        self.ws_manager = ws_manager

        self.scheduler = AsyncIOScheduler(timezone=settings.scheduler.timezone)
        self.weather_client = WeatherClient(settings.weather)
        self.ai_manager = AIManager(settings)

    async def start(self) -> None:
        """Start the scheduler."""
        tz = ZoneInfo(self.settings.scheduler.timezone)

        # Schedule hourly refresh
        job = self.scheduler.add_job(
            self.try_refresh_weather,
            CronTrigger(
                minute=self.settings.scheduler.refresh_minute,
                timezone=tz,
            ),
            id="weather_refresh",
            max_instances=1,
            replace_existing=True,
        )

        if await self.needs_refresh():
            # Initiate refresh immediately if needed
            logger.info("refresh_immediately")
            job.modify(next_run_time=datetime.now(tz))

        self.scheduler.start()
        logger.info("scheduler_started")
        logger.info("scheduler_jobs", jobs=[job.next_run_time for job in self.scheduler.get_jobs()])

    async def try_refresh_weather(self) -> None:
        """Fetch weather and generate visualizations with progressive updates."""
        try:
            await self.refresh_weather()
        except Exception as e:
            logger.error("refresh_failed", error=str(e))

    async def refresh_weather(self) -> None:
        """Fetch weather and generate visualizations with progressive updates."""
        timestamp = datetime.now().replace(minute=0, second=0, microsecond=0)
        logger.info("refresh_started", timestamp=timestamp.isoformat())

        weather_json: str = await self.weather_client.get_current_weather()

        models = self.settings.get_enabled_ai_model_names()
        await self.archive.save_metadata(timestamp, models, self.settings.prompt.template)
        await self.archive.save_weather(timestamp, weather_json)

        # Update state and broadcast weather data
        weather_dict = json.loads(weather_json)
        self.state_service.update_timestamp(timestamp.isoformat())
        self.state_service.update_weather(weather_dict)
        await self.ws_manager.broadcast_weather()

        # Broadcast visualizations, so clients realize we're generating new ones
        for model_name in models:
            await self.ws_manager.broadcast_visualization(model_name)

        # Define callback for progressive updates
        async def on_visualization_complete(model_name: str, html: str) -> None:
            """Called when each model completes."""
            await self.archive.save_visualization(timestamp, model_name, html)
            self.state_service.update_visualization(model_name, html)
            await self.ws_manager.broadcast_visualization(model_name)

        # Generate visualizations with progressive updates
        visualizations = await self.ai_manager.generate_all(weather_json, on_complete=on_visualization_complete)

        logger.info("refresh_complete", models=len(visualizations))

    async def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("scheduler_stopped")

    async def needs_refresh(self) -> bool:
        timestamp_str = self.state_service.current_timestamp
        if timestamp_str is None:
            logger.info("no_cached_data_found")
            return True

        timestamp = datetime.fromisoformat(timestamp_str)
        age = datetime.now(timestamp.tzinfo) - timestamp

        logger.info("cached_data_age", age_hours=age.total_seconds() / 3600)
        if age > timedelta(hours=1):
            logger.info("cached_data_too_old")
            return True

        missing_models = await self.archive.get_missing_models(timestamp, self.settings.get_enabled_ai_model_names())

        if len(missing_models) > 0:
            logger.info("cached_data_missing_models", models=missing_models)
            return True

        return False
