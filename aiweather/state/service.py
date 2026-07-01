"""Simple state service for holding current weather data and visualizations."""

from typing import Any

import structlog

from ..visualization import Visualization, VisualizationStatus

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class StateService:
    """Holds current weather state and provides a simple update/read interface.

    This is a passive data holder - it doesn't broadcast, notify, or load from disk.
    Other components update it and read from it directly.
    """

    def __init__(self) -> None:
        self.current_weather: dict[str, Any] | None = None
        self.current_visualizations: dict[str, Visualization] = {}
        self.current_timestamp: str | None = None
        self.visualization_status: dict[str, VisualizationStatus] = {}

    def install_initial_state(
        self,
        timestamp: str | None,
        weather: dict[str, Any] | None,
        visualizations: dict[str, Visualization],
    ) -> None:
        """Replace state wholesale with data loaded from the archive.

        Seeds both the visualization map and its parallel status map.
        """
        self.current_timestamp = timestamp
        self.current_weather = weather
        self.current_visualizations = dict(visualizations)
        self.visualization_status = {name: VisualizationStatus.UP_TO_DATE for name in visualizations}

    def update_timestamp(self, timestamp: str) -> None:
        self.current_timestamp = timestamp

    def update_weather(self, weather: dict[str, Any]) -> None:
        self.current_weather = weather
        logger.debug("state_weather_updated", weather=weather)

    def update_visualization(self, model_name: str, visualization: Visualization) -> None:
        self.current_visualizations[model_name] = visualization
        logger.debug("state_viz_updated", model=model_name)

    def mark_all_outdated(self) -> None:
        """Mark every current visualization as outdated."""
        for name in self.current_visualizations:
            self.visualization_status[name] = VisualizationStatus.OUTDATED

    def mark_generating(self, model_name: str) -> None:
        self.visualization_status[model_name] = VisualizationStatus.GENERATING

    def mark_up_to_date(self, model_name: str) -> None:
        self.visualization_status[model_name] = VisualizationStatus.UP_TO_DATE
