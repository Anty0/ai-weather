"""OpenWeather API client."""

import json

import httpx
import structlog

from ..config import WeatherConfig

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class WeatherClient:
    """OpenWeather API client."""

    def __init__(self, config: WeatherConfig) -> None:
        """Initialize weather client.

        Args:
            config: Weather configuration
        """
        self.config = config
        self.base_url = "https://api.openweathermap.org/data/3.0"

    async def get_current_weather(self) -> str:
        """Fetch current weather data from OpenWeather One Call API 3.0.

        Returns:
            Raw JSON string from API response

        Raises:
            httpx.HTTPStatusError: If API request fails
            ValueError: If response is not valid JSON
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/onecall",
                params={
                    "lat": self.config.lat,
                    "lon": self.config.lon,
                    "appid": self.config.api_key,
                    "units": self.config.units,
                },
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            weather = response.json()
            current = weather["current"]
            current_str = json.dumps(current)

            logger.info("weather_fetched", api_version="3.0")

            return current_str
