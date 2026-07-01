"""Tests for the OpenWeather client (httpx mocked)."""

import json

import httpx

from aiweather.config import WeatherConfig
from aiweather.weather import WeatherClient


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class FakeAsyncClient:
    last_params: dict | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None, timeout=None):
        FakeAsyncClient.last_params = params
        return FakeResponse({"current": {"temp": 9, "humidity": 42}, "hourly": [{"temp": 8}]})


async def test_returns_current_block_only(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    client = WeatherClient(WeatherConfig(api_key="k", lat=50.0, lon=14.0))
    result = await client.get_current_weather()
    assert json.loads(result) == {"temp": 9, "humidity": 42}
    assert FakeAsyncClient.last_params["lat"] == 50.0
    assert FakeAsyncClient.last_params["appid"] == "k"
