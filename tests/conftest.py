"""Shared fixtures and fakes for the AI Weather test suite."""

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from aiweather.ai.base import AIProvider
from aiweather.config import (
    AIConfig,
    AIModelConfig,
    OllamaConfig,
    PromptConfig,
    SchedulerConfig,
    Settings,
    StorageConfig,
    WeatherConfig,
)

PROMPT_TEMPLATE = "Render this weather visually:\n{weather_json}\nOutput only HTML."


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """Run every test from an empty CWD so config.yaml/.env in the repo never leak in."""
    monkeypatch.chdir(tmp_path)


def make_settings(
    *,
    tz: str = "UTC",
    models: list[AIModelConfig] | None = None,
    progress_interval_seconds: float = 0,
    readiness_probe_timeout_seconds: float = 3,
    max_concurrent: int = 0,
    data_dir=None,
) -> Settings:
    if models is None:
        models = [AIModelConfig(name="Model One", provider="ollama", model_id="m1")]
    storage = StorageConfig(data_dir=data_dir) if data_dir is not None else StorageConfig()
    return Settings(
        weather=WeatherConfig(api_key="test-key", lat=50.0, lon=14.0),
        ai_models=models,
        ai=AIConfig(
            max_concurrent=max_concurrent,
            progress_interval_seconds=progress_interval_seconds,
            readiness_probe_timeout_seconds=readiness_probe_timeout_seconds,
        ),
        ollama=OllamaConfig(),
        prompt=PromptConfig(template=PROMPT_TEMPLATE),
        scheduler=SchedulerConfig(timezone=tz),
        storage=storage,
    )


class FakeProvider(AIProvider):
    """AIProvider double: streams configured deltas and reports configured availability."""

    def __init__(
        self,
        deltas: list[str] | None = None,
        *,
        available: bool = True,
        available_error: BaseException | None = None,
        available_sleep: float = 0.0,
        generate_error: BaseException | None = None,
        generate_sleep: float = 0.0,
    ) -> None:
        self.deltas = deltas if deltas is not None else ["<p>ok</p>"]
        self.available = available
        self.available_error = available_error
        self.available_sleep = available_sleep
        self.generate_error = generate_error
        self.generate_sleep = generate_sleep

    async def generate_html(
        self,
        prompt: str,
        model_id: str,
        on_chunk: Callable[[str], Awaitable[None]] | None = None,
        **kwargs: object,
    ) -> str:
        if self.generate_sleep:
            await asyncio.sleep(self.generate_sleep)
        if self.generate_error is not None:
            raise self.generate_error
        accumulated = ""
        for delta in self.deltas:
            accumulated += delta
            if on_chunk:
                await on_chunk(accumulated)
        return accumulated

    async def is_available(self) -> bool:
        if self.available_sleep:
            await asyncio.sleep(self.available_sleep)
        if self.available_error is not None:
            raise self.available_error
        return self.available


class RecordingConnectionManager:
    """ConnectionManager double capturing broadcast calls."""

    def __init__(self) -> None:
        self.weather_broadcasts = 0
        self.visualization_broadcasts: list[str] = []

    async def broadcast_weather(self) -> None:
        self.weather_broadcasts += 1

    async def broadcast_visualization(self, model_name: str) -> None:
        self.visualization_broadcasts.append(model_name)


class FakeWeatherClient:
    def __init__(
        self,
        weather_json: str = '{"temp": 21, "humidity": 50}',
        *,
        error: BaseException | None = None,
    ) -> None:
        self.weather_json = weather_json
        self.error = error

    async def get_current_weather(self) -> str:
        if self.error is not None:
            raise self.error
        return self.weather_json


class FakeWebSocket:
    """Minimal WebSocket double for testing send/broadcast cleanup paths."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[dict] = []
        self.client = "test-client"

    async def send_json(self, message: dict) -> None:
        if self.fail:
            raise RuntimeError("send failed")
        self.sent.append(message)
