"""Refresh orchestration for AI Weather."""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import structlog

from ..ai import AIManager
from ..config import Settings
from ..state import StateService
from ..storage import ArchiveManager
from ..visualization import HtmlNormalizer, Visualization
from ..weather import WeatherClient
from ..websocket import ConnectionManager

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class RefreshService:
    """Orchestrates a full refresh cycle: fetch -> archive -> state -> broadcast -> generate."""

    def __init__(
        self,
        settings: Settings,
        weather_client: WeatherClient,
        ai_manager: AIManager,
        archive: ArchiveManager,
        state_service: StateService,
        ws_manager: ConnectionManager,
        normalizer: HtmlNormalizer | None = None,
    ) -> None:
        """Initialize the refresh service.

        Args:
            settings: Application settings
            weather_client: OpenWeather client
            ai_manager: AI manager that generates visualizations
            archive: Archive manager for disk persistence
            state_service: In-memory state holder
            ws_manager: WebSocket connection manager for broadcasts
            normalizer: Shared HTML normalizer (created if not provided)
        """
        self.settings = settings
        self.weather_client = weather_client
        self.ai_manager = ai_manager
        self.archive = archive
        self.state_service = state_service
        self.ws_manager = ws_manager
        self.normalizer = normalizer or HtmlNormalizer()
        self.tz = ZoneInfo(settings.scheduler.timezone)

    async def load_initial_state(self) -> bool:
        """Load the latest archived data into state, normalizing raw HTML on the way in."""
        latest = await self.archive.load_latest(self.settings.get_enabled_ai_model_names())
        if not latest:
            logger.info("no_archive_data", action="starting_with_empty_state")
            return False

        raw_visualizations: dict[str, str] = latest.get("visualizations", {})
        visualizations = {
            name: Visualization.from_raw(raw, self.normalizer) for name, raw in raw_visualizations.items()
        }
        self.state_service.install_initial_state(
            latest["timestamp"],
            latest.get("weather"),
            visualizations,
        )
        logger.info(
            "state_loaded_from_archive",
            timestamp=latest["timestamp"],
            has_weather=bool(latest.get("weather")),
            viz_count=len(visualizations),
        )
        return True

    async def needs_refresh(self) -> bool:
        timestamp_str = self.state_service.current_timestamp
        if timestamp_str is None:
            logger.info("no_cached_data_found")
            return True

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.info("unparseable_timestamp", timestamp=timestamp_str, action="forcing_refresh")
            return True
        if timestamp.tzinfo is None:
            logger.info("legacy_naive_timestamp", action="forcing_refresh")
            return True

        age = datetime.now(self.tz) - timestamp
        logger.info("cached_data_age", age_hours=age.total_seconds() / 3600)
        if age > timedelta(hours=1):
            logger.info("cached_data_too_old")
            return True

        missing_models = await self.archive.get_missing_models(timestamp, self.settings.get_enabled_ai_model_names())
        if missing_models:
            logger.info("cached_data_missing_models", models=missing_models)
            return True

        return False

    async def try_refresh_weather(self) -> None:
        """Run a refresh cycle, swallowing errors so the scheduler stays alive."""
        try:
            await self.refresh_weather()
        except Exception as e:
            logger.error("refresh_failed", error=str(e))

    async def refresh_weather(self) -> None:
        """Fetch weather and generate visualizations with progressive updates."""
        timestamp = datetime.now(self.tz).replace(minute=0, second=0, microsecond=0)
        logger.info("refresh_started", timestamp=timestamp.isoformat())

        weather_json = await self.weather_client.get_current_weather()

        models = self.settings.get_enabled_ai_model_names()
        await self.archive.save_metadata(timestamp, models, self.settings.prompt.template)
        await self.archive.save_weather(timestamp, weather_json)

        weather_dict = json.loads(weather_json)
        self.state_service.update_timestamp(timestamp.isoformat())
        self.state_service.update_weather(weather_dict)
        self.state_service.mark_all_outdated()
        await self.ws_manager.broadcast_weather()

        for model_name in models:
            await self.ws_manager.broadcast_visualization(model_name)

        async def on_update(model_name: str, visualization: Visualization, is_complete: bool) -> None:
            await self.archive.save_visualization(timestamp, model_name, visualization.raw)
            self.state_service.update_visualization(model_name, visualization)
            if is_complete:
                self.state_service.mark_up_to_date(model_name)
            else:
                self.state_service.mark_generating(model_name)
            await self.ws_manager.broadcast_visualization(model_name)

        visualizations = await self.ai_manager.generate_all(weather_json, on_update=on_update)
        logger.info("refresh_complete", models=len(visualizations))
