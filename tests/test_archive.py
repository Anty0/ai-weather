"""Tests for the ArchiveManager disk round-trip."""

from datetime import UTC, datetime

import pytest

from aiweather.storage import ArchiveManager


@pytest.fixture
def archive(tmp_path):
    return ArchiveManager(tmp_path / "data")


TS = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


async def test_save_and_load_round_trip(archive):
    models = ["Model One", "Model Two"]
    await archive.save_metadata(TS, models, "template {weather_json}")
    await archive.save_weather(TS, '{"temp": 20}')
    await archive.save_visualization(TS, "Model One", "<h1>one</h1>")

    loaded = await archive.load_hour(TS, models)
    assert loaded is not None
    assert loaded["timestamp"] == TS.isoformat()
    assert loaded["weather"] == {"temp": 20}
    assert loaded["visualizations"] == {"Model One": "<h1>one</h1>"}


async def test_load_returns_raw_html_unmodified(archive):
    raw = "```html\n<h1>fenced</h1>\n```"
    await archive.save_metadata(TS, ["Model One"], "t {weather_json}")
    await archive.save_visualization(TS, "Model One", raw)
    loaded = await archive.load_hour(TS, ["Model One"])
    assert loaded["visualizations"]["Model One"] == raw


async def test_get_missing_models(archive):
    await archive.save_metadata(TS, ["Model One", "Model Two"], "t {weather_json}")
    await archive.save_visualization(TS, "Model One", "<h1>one</h1>")
    missing = await archive.get_missing_models(TS, ["Model One", "Model Two"])
    assert missing == ["Model Two"]


async def test_find_latest_dir(archive):
    older = datetime(2026, 6, 1, 8, 0, 0, tzinfo=UTC)
    await archive.save_metadata(older, ["Model One"], "t {weather_json}")
    await archive.save_metadata(TS, ["Model One"], "t {weather_json}")
    latest = archive.find_latest_dir()
    assert latest is not None
    assert latest.name == "01-12"


async def test_load_latest_none_when_empty(archive):
    assert await archive.load_latest(["Model One"]) is None
