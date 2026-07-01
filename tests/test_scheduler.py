"""Tests for WeatherScheduler's startup immediate-refresh decision."""

import asyncio

from aiweather.scheduler import WeatherScheduler
from tests.conftest import make_settings


class FakeRefresh:
    def __init__(self, needs: bool) -> None:
        self._needs = needs
        self.ran = False

    async def needs_refresh(self) -> bool:
        return self._needs

    async def try_refresh_weather(self) -> None:
        self.ran = True


async def _run_start(needs: bool) -> FakeRefresh:
    fake = FakeRefresh(needs)
    scheduler = WeatherScheduler(make_settings(tz="UTC"), fake)
    await scheduler.start()
    await asyncio.sleep(0.2)  # give APScheduler a chance to fire an immediate job
    await scheduler.stop()
    return fake


async def test_start_runs_immediately_when_stale():
    fake = await _run_start(True)
    assert fake.ran is True


async def test_start_does_not_run_when_fresh():
    fake = await _run_start(False)
    assert fake.ran is False
