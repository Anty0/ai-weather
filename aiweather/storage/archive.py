import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class ArchiveManager:
    """Manages weather visualization archives."""

    def __init__(self, base_dir: Path) -> None:
        """Initialize archive manager.

        Args:
            base_dir: Base directory for archives
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_hourly_dir(self, timestamp: datetime) -> Path:
        """Get directory for specific hour.

        Args:
            timestamp: Timestamp to get directory for

        Returns:
            Path to hourly directory (data/YYYY-MM/DD-HH)
        """
        year_month = timestamp.strftime("%Y-%m")
        day_hour = timestamp.strftime("%d-%H")
        return self.base_dir / year_month / day_hour

    @staticmethod
    def get_model_filename(model_name: str) -> str:
        """Get path to specific visualization for a specific hour."""

        safe_name = model_name.replace(" ", "_").replace("/", "_")
        return f"{safe_name}.html"

    def find_latest_dir(self) -> Optional[Path]:
        """Find the most recent hourly directory."""
        latest_year_month = max((d for d in self.base_dir.iterdir() if d.is_dir()), key=lambda p: p.name, default=None)
        if not latest_year_month:
            return None

        latest_day_hour = max(
            (d for d in latest_year_month.iterdir() if d.is_dir()), key=lambda p: p.name, default=None
        )
        if not latest_day_hour:
            return None

        logger.info(
            "latest_found",
            year_month=latest_year_month.name,
            day_hour=latest_day_hour.name,
        )
        return latest_day_hour

    async def save_metadata(
        self,
        timestamp: datetime,
        models: List[str],
        prompt: str,
    ) -> Path:
        """Save metadata.

        Args:
            timestamp: Hour timestamp
            models: List of model names that will generate visualizations
            prompt: Prompt template used to generate visualizations

        Returns:
            Path to hourly directory
        """
        hour_dir = self.get_hourly_dir(timestamp)
        hour_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "timestamp": timestamp.isoformat(),
            "models": models,
            "prompt": prompt,
        }
        async with aiofiles.open(hour_dir / "metadata.json", "w") as f:
            await f.write(json.dumps(metadata, indent=2))

        logger.info(
            "metadata_saved",
            timestamp=timestamp.isoformat(),
            expected_models=len(models),
        )

        return hour_dir

    async def save_weather(
        self,
        timestamp: datetime,
        weather_json: str,
    ) -> Path:
        """Save weather data.

        Args:
            timestamp: Hour timestamp
            weather_json: Weather data

        Returns:
            Path to hourly directory
        """
        hour_dir = self.get_hourly_dir(timestamp)
        hour_dir.mkdir(parents=True, exist_ok=True)

        # Save weather data
        async with aiofiles.open(hour_dir / "weather.json", "w") as f:
            await f.write(weather_json)

        logger.info(
            "weather_saved",
            timestamp=timestamp.isoformat(),
        )

        return hour_dir

    async def save_visualization(self, timestamp: datetime, model_name: str, html: str) -> None:
        """Save individual visualization.

        Args:
            timestamp: Hour timestamp
            model_name: Name of the AI model
            html: Generated HTML content
        """
        hour_dir = self.get_hourly_dir(timestamp)
        hour_dir.mkdir(parents=True, exist_ok=True)

        # Save HTML
        model_path = hour_dir / self.get_model_filename(model_name)
        async with aiofiles.open(model_path, "w") as f:
            await f.write(html)

        logger.info("visualization_saved", timestamp=timestamp.isoformat(), model=model_name)

    async def load_latest(self, models: List[str]) -> Optional[Dict[str, Any]]:
        """Load the most recent hour's data.

        Args:
            models: List of model names to load

        Returns:
            Dictionary with timestamp, weather, and visualizations, or None if no data
        """
        if not self.base_dir.exists():
            return None

        # Find the most recent directory
        latest_dir = self.find_latest_dir()
        if not latest_dir:
            return None

        return await self._load_hour_data(latest_dir, models)

    async def load_hour(self, timestamp: datetime, models: List[str]) -> Optional[Dict[str, Any]]:
        """Load data for a specific hour.

        Args:
            timestamp: Hour timestamp
            models: List of model names to load

        Returns:
            Dictionary with timestamp, weather, and visualizations, or None if not found
        """
        hour_dir = self.get_hourly_dir(timestamp)
        if not hour_dir.exists():
            return None

        return await self._load_hour_data(hour_dir, models)

    async def get_missing_models(self, timestamp: datetime, models: List[str]) -> List[str]:
        """Get a list of models that haven't completed for this hour.

        Useful for resuming after restart.

        Args:
            timestamp: Hour timestamp
            models: List of model names to check

        Returns:
            List of model names that are expected but missing
        """

        hour_dir = self.get_hourly_dir(timestamp)
        return [model for model in models if not (hour_dir / self.get_model_filename(model)).exists()]

    async def _load_hour_data(self, hour_dir: Path, models: List[str]) -> Dict[str, Any]:
        """Load data from a specific hour directory.

        Args:
            hour_dir: Path to hour directory

        Returns:
            Dictionary with timestamp, weather, and visualizations
        """
        # Load weather data
        weather_path = hour_dir / "weather.json"
        weather_data = None
        if weather_path.exists():
            async with aiofiles.open(weather_path, "r") as f:
                weather_data = json.loads(await f.read())

        metadata_path = hour_dir / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            async with aiofiles.open(metadata_path, "r") as f:
                metadata = json.loads(await f.read())

        visualizations = {}
        missing_models = []
        for model_name in models:
            model_path = hour_dir / self.get_model_filename(model_name)
            if model_path.exists():
                async with aiofiles.open(model_path, "r") as f:
                    visualizations[model_name] = await f.read()
            else:
                missing_models.append(model_name)

        return {
            "timestamp": metadata.get("timestamp", hour_dir.name),
            "weather": weather_data,
            "visualizations": visualizations,
            "missing_visualizations": missing_models,
        }
