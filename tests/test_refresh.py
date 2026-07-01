"""Tests for RefreshService orchestration, load, and needs_refresh."""

from datetime import UTC, datetime, timedelta

from aiweather.ai import AIManager
from aiweather.state import StateService
from aiweather.storage import ArchiveManager
from aiweather.visualization import HtmlNormalizer
from tests.conftest import FakeProvider, FakeWeatherClient, RecordingConnectionManager, make_settings

FENCED = ["```html\n", "<p>hi</p>\n", "```"]
FINAL_RAW = "```html\n<p>hi</p>\n```"
WEATHER = '{"temp": 20}'


def make_service(tmp_path, *, settings=None, provider=None, state=None, ws=None):
    settings = settings or make_settings(tz="UTC")
    state = state or StateService()
    ws = ws or RecordingConnectionManager()
    normalizer = HtmlNormalizer()
    archive = ArchiveManager(tmp_path / "data")
    ai_manager = AIManager(settings, {"ollama": provider or FakeProvider(FENCED)}, normalizer)
    from aiweather.scheduler import RefreshService

    service = RefreshService(
        settings,
        FakeWeatherClient(WEATHER),
        ai_manager,
        archive,
        state,
        ws,
        normalizer,
    )
    return service, state, ws, archive


async def test_needs_refresh_true_when_no_timestamp(tmp_path):
    service, *_ = make_service(tmp_path)
    assert await service.needs_refresh() is True


async def test_needs_refresh_false_for_recent_with_all_models(tmp_path):
    service, state, _ws, archive = make_service(tmp_path)
    ts = datetime.now(UTC) - timedelta(minutes=30)
    await archive.save_visualization(ts, "Model One", FINAL_RAW)
    state.current_timestamp = ts.isoformat()
    assert await service.needs_refresh() is False


async def test_needs_refresh_true_when_too_old(tmp_path):
    service, state, _ws, archive = make_service(tmp_path)
    ts = datetime.now(UTC) - timedelta(minutes=61)
    await archive.save_visualization(ts, "Model One", FINAL_RAW)
    state.current_timestamp = ts.isoformat()
    assert await service.needs_refresh() is True


async def test_needs_refresh_true_when_model_missing(tmp_path):
    service, state, *_ = make_service(tmp_path)
    ts = datetime.now(UTC) - timedelta(minutes=10)
    state.current_timestamp = ts.isoformat()
    assert await service.needs_refresh() is True


async def test_needs_refresh_true_for_legacy_naive_timestamp(tmp_path):
    service, state, *_ = make_service(tmp_path)
    state.current_timestamp = "2026-07-01T12:00:00"
    assert await service.needs_refresh() is True


async def test_refresh_cycle_writes_state_broadcasts_and_raw(tmp_path):
    service, state, ws, archive = make_service(tmp_path)
    await service.refresh_weather()

    assert state.current_weather == {"temp": 20}
    assert datetime.fromisoformat(state.current_timestamp).tzinfo is not None
    assert state.current_visualizations["Model One"].normalized == "<p>hi</p>"
    assert ws.weather_broadcasts >= 1
    assert "Model One" in ws.visualization_broadcasts

    loaded = await archive.load_latest(["Model One"])
    assert loaded["visualizations"]["Model One"] == FINAL_RAW


async def test_needs_refresh_false_immediately_after_refresh(tmp_path):
    service, *_ = make_service(tmp_path)
    await service.refresh_weather()
    assert await service.needs_refresh() is False


async def test_load_initial_state_round_trip_restores_and_normalizes(tmp_path):
    writer, _state, _ws, _archive = make_service(tmp_path)
    await writer.refresh_weather()

    reader, state2, _ws2, _archive2 = make_service(tmp_path, state=StateService())
    loaded = await reader.load_initial_state()

    assert loaded is True
    assert state2.current_weather == {"temp": 20}
    assert datetime.fromisoformat(state2.current_timestamp).tzinfo is not None
    viz = state2.current_visualizations["Model One"]
    assert viz.raw == FINAL_RAW
    assert viz.normalized == "<p>hi</p>"
    assert await reader.needs_refresh() is False


async def test_try_refresh_weather_swallows_errors(tmp_path):
    settings = make_settings(tz="UTC")
    state = StateService()
    ws = RecordingConnectionManager()
    normalizer = HtmlNormalizer()
    archive = ArchiveManager(tmp_path / "data")
    ai_manager = AIManager(settings, {"ollama": FakeProvider(FENCED)}, normalizer)
    from aiweather.scheduler import RefreshService

    service = RefreshService(
        settings,
        FakeWeatherClient(error=RuntimeError("api down")),
        ai_manager,
        archive,
        state,
        ws,
        normalizer,
    )
    await service.try_refresh_weather()


async def test_needs_refresh_forces_when_metadata_missing(tmp_path):
    service, state, _ws, archive = make_service(tmp_path)
    ts = datetime.now(UTC)
    await archive.save_visualization(ts, "Model One", FINAL_RAW)
    loaded = await service.load_initial_state()
    assert loaded is True
    assert await service.needs_refresh() is True


async def test_load_initial_state_false_when_empty(tmp_path):
    service, *_ = make_service(tmp_path)
    assert await service.load_initial_state() is False


async def test_mark_all_outdated_after_load(tmp_path):
    writer, *_ = make_service(tmp_path)
    await writer.refresh_weather()
    reader, state2, _ws2, _archive2 = make_service(tmp_path, state=StateService())
    await reader.load_initial_state()
    state2.mark_all_outdated()
    from aiweather.visualization import VisualizationStatus

    assert state2.visualization_status["Model One"] == VisualizationStatus.OUTDATED
