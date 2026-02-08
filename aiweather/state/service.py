"""Simple state service for holding current weather data and visualizations."""

from typing import Any, Dict, Optional

import structlog

from ..config import Settings
from ..storage import ArchiveManager

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class StateService:
    """Holds current weather state and provides simple update/read interface.

    This is a passive data holder - it doesn't broadcast or notify.
    Other components update it and read from it directly.
    """

    def __init__(self, archive: ArchiveManager, settings: Settings) -> None:
        """Initialize state service.

        Args:
            archive: Archive manager for loading initial state
            settings: Application settings for enabled models
        """
        self.archive = archive
        self.settings = settings

        # State
        self.current_weather: Optional[Dict[str, Any]] = None
        self.current_visualizations: Dict[str, str] = {}
        self.current_timestamp: Optional[str] = None
        self.visualization_status: Dict[str, str] = {}

    async def load_from_archive(self) -> bool:
        """Load the latest data from the archive into state.

        Called on startup to initialize state from disk.

        Returns:
            True if data was loaded, False if no archive data exists
        """
        latest = await self.archive.load_latest(self.settings.get_enabled_ai_model_names())

        if not latest:
            logger.info("no_archive_data", action="starting_with_empty_state")
            return False

        self.current_timestamp = latest["timestamp"]
        self.current_weather = latest.get("weather")
        self.current_visualizations = latest.get("visualizations", {})
        self.visualization_status = {name: "up_to_date" for name in self.current_visualizations}

        logger.info(
            "state_loaded_from_archive",
            timestamp=self.current_timestamp,
            has_weather=bool(self.current_weather),
            viz_count=len(self.current_visualizations),
        )
        return True

    def update_timestamp(self, timestamp: str) -> None:
        """Update current timestamp.

        Args:
            timestamp: ISO format timestamp string
        """
        self.current_timestamp = timestamp

    def update_weather(self, weather: Dict[str, Any]) -> None:
        """Update current weather data.

        Args:
            weather: Weather data dictionary
        """
        self.current_weather = weather
        logger.debug("state_weather_updated", weather=weather)

    def update_visualization(self, model_name: str, html: str) -> None:
        """Update a visualization.

        Args:
            model_name: Name of the AI model
            html: Generated HTML content
        """
        self.current_visualizations[model_name] = html
        logger.debug("state_viz_updated", model=model_name)

    def mark_all_outdated(self) -> None:
        """Mark all visualizations as outdated."""
        for name in self.visualization_status:
            self.visualization_status[name] = "outdated"

    def mark_generating(self, model_name: str) -> None:
        """Mark a visualization as currently generating."""
        self.visualization_status[model_name] = "generating"

    def mark_up_to_date(self, model_name: str) -> None:
        """Mark a visualization as up to date."""
        self.visualization_status[model_name] = "up_to_date"
