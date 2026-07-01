"""Tests for AIManager orchestration, progressive updates, and error rendering."""

import asyncio

from aiweather.ai import AIManager
from aiweather.config import AIModelConfig
from aiweather.visualization import HtmlNormalizer, Visualization
from tests.conftest import FakeProvider, make_settings


class PeakTrackingProvider(FakeProvider):
    """Records the peak number of concurrent generate_html calls."""

    def __init__(self):
        super().__init__(["<p>x</p>"])
        self._current = 0
        self.peak = 0
        self._lock = asyncio.Lock()

    async def generate_html(self, prompt, model_id, on_chunk=None, **kwargs):
        async with self._lock:
            self._current += 1
            self.peak = max(self.peak, self._current)
        await asyncio.sleep(0.02)
        async with self._lock:
            self._current -= 1
        return "<p>x</p>"


def three_models():
    return [AIModelConfig(name=f"M{i}", provider="ollama", model_id=str(i)) for i in range(3)]


WEATHER = '{"temp": 20}'
FENCED = ["```html\n", "<p>hi</p>\n", "```"]


def collector():
    calls: list[tuple[str, Visualization, bool]] = []

    async def on_update(model_name, visualization, is_complete):
        calls.append((model_name, visualization, is_complete))

    return calls, on_update


async def test_generate_all_returns_visualizations():
    settings = make_settings()
    manager = AIManager(settings, {"ollama": FakeProvider(FENCED)})
    result = await manager.generate_all(WEATHER)
    assert set(result) == {"Model One"}
    viz = result["Model One"]
    assert isinstance(viz, Visualization)
    assert viz.raw == "```html\n<p>hi</p>\n```"
    assert viz.normalized == "<p>hi</p>"


async def test_error_branch_returns_error_html_and_fires_complete():
    settings = make_settings()
    provider = FakeProvider(generate_error=RuntimeError("boom"))
    manager = AIManager(settings, {"ollama": provider})
    calls, on_update = collector()
    result = await manager.generate_all(WEATHER, on_update=on_update)

    assert "Generation failed" in result["Model One"].raw
    assert calls[-1][2] is True


async def test_timeout_yields_error_visualization():
    models = [AIModelConfig(name="Slow", provider="ollama", model_id="s", timeout=1)]
    settings = make_settings(models=models)
    provider = FakeProvider(generate_sleep=5)
    manager = AIManager(settings, {"ollama": provider})
    result = await manager.generate_all(WEATHER)
    assert "Generation failed" in result["Slow"].raw


async def test_concurrency_limit_bounds_parallelism():
    settings = make_settings(models=three_models(), max_concurrent=1)
    provider = PeakTrackingProvider()
    manager = AIManager(settings, {"ollama": provider})
    result = await manager.generate_all(WEATHER)
    assert set(result) == {"M0", "M1", "M2"}
    assert provider.peak == 1


async def test_unbounded_runs_models_in_parallel():
    settings = make_settings(models=three_models(), max_concurrent=0)
    provider = PeakTrackingProvider()
    manager = AIManager(settings, {"ollama": provider})
    await manager.generate_all(WEATHER)
    assert provider.peak > 1


async def test_progressive_frames_are_normalized_per_frame():
    settings = make_settings(progress_interval_seconds=0)
    manager = AIManager(settings, {"ollama": FakeProvider(FENCED)})
    calls, on_update = collector()
    await manager.generate_all(WEATHER, on_update=on_update)

    reference = HtmlNormalizer()
    intermediates = [c for c in calls if c[2] is False]
    completions = [c for c in calls if c[2] is True]

    assert len(completions) == 1
    assert intermediates, "expected progressive frames with interval=0"
    for _name, viz, _done in intermediates:
        assert viz.normalized is not None
        assert viz.normalized == reference.normalize(viz.raw)

    final = completions[0][1]
    assert "```" not in final.normalized
    assert final.normalized == "<p>hi</p>"


async def test_throttle_suppresses_intermediate_frames():
    settings = make_settings(progress_interval_seconds=30)
    manager = AIManager(settings, {"ollama": FakeProvider(FENCED)})
    calls, on_update = collector()
    await manager.generate_all(WEATHER, on_update=on_update)

    intermediates = [c for c in calls if c[2] is False]
    completions = [c for c in calls if c[2] is True]
    assert len(intermediates) < len(FENCED)
    assert len(completions) == 1


async def test_malformed_weather_json_still_generates():
    settings = make_settings()
    manager = AIManager(settings, {"ollama": FakeProvider(["<p>x</p>"])})
    result = await manager.generate_all("not valid json")
    assert result["Model One"].raw == "<p>x</p>"


async def test_missing_provider_yields_error_visualization():
    models = [AIModelConfig(name="A", provider="ollama", model_id="a")]
    settings = make_settings(models=models)
    manager = AIManager(settings, {})
    result = await manager.generate_all(WEATHER)
    assert "Generation failed" in result["A"].raw


async def test_error_html_escapes_special_characters():
    settings = make_settings()
    manager = AIManager(settings, {"ollama": FakeProvider()})
    html = manager._error_html("Model {name}", 'boom <script> {error} & "x"')
    assert "&lt;script&gt;" in html
    assert "{name}" in html
    assert "<script>" not in html
