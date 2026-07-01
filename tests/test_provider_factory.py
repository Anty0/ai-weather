"""Tests for the provider factory and availability probe."""

import asyncio

from aiweather.ai import default_provider_factory, probe_all, probe_available
from aiweather.config import AIModelConfig
from tests.conftest import FakeProvider, make_settings


def test_builds_only_enabled_model_providers():
    settings = make_settings(
        models=[
            AIModelConfig(name="A", provider="ollama", model_id="a"),
            AIModelConfig(name="B", provider="ollama", model_id="b", enabled=False),
        ]
    )
    providers = default_provider_factory(settings)
    assert set(providers) == {"ollama"}


def test_unknown_provider_skipped_not_fatal():
    settings = make_settings(
        models=[
            AIModelConfig(name="A", provider="mystery", model_id="a"),
            AIModelConfig(name="B", provider="ollama", model_id="b"),
        ]
    )
    providers = default_provider_factory(settings)
    assert set(providers) == {"ollama"}


def test_shared_provider_built_once():
    settings = make_settings(
        models=[
            AIModelConfig(name="A", provider="ollama", model_id="a"),
            AIModelConfig(name="B", provider="ollama", model_id="b"),
        ]
    )
    providers = default_provider_factory(settings)
    assert list(providers) == ["ollama"]


async def test_probe_available_true():
    assert await probe_available(FakeProvider(available=True), 1) is True


async def test_probe_available_false():
    assert await probe_available(FakeProvider(available=False), 1) is False


async def test_probe_available_swallows_error():
    assert await probe_available(FakeProvider(available_error=RuntimeError("down")), 1) is False


async def test_probe_available_bounded_by_timeout():
    slow = FakeProvider(available_sleep=1.0)
    result = await asyncio.wait_for(probe_available(slow, 0.05), timeout=0.5)
    assert result is False


async def test_probe_all_maps_names():
    providers = {"ollama": FakeProvider(available=True), "other": FakeProvider(available=False)}
    assert await probe_all(providers, 1) == {"ollama": True, "other": False}
