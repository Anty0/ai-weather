"""Tests for configuration loading and the prompt-template validator."""

import pytest
from pydantic import ValidationError

from aiweather.config import PromptConfig
from tests.conftest import make_settings


def test_defaults_applied():
    settings = make_settings()
    assert settings.ai.max_concurrent == 0
    assert settings.scheduler.refresh_minute == 0
    assert settings.weather.units == "metric"


def test_env_override(monkeypatch):
    monkeypatch.setenv("WEATHER__API_KEY", "from-env")
    monkeypatch.setenv("SCHEDULER__TIMEZONE", "Europe/Prague")
    from aiweather.config import Settings

    settings = Settings(
        weather={"lat": 1.0, "lon": 2.0},  # type: ignore[arg-type]
        prompt={"template": "x {weather_json} y"},  # type: ignore[arg-type]
    )
    assert settings.weather.api_key == "from-env"
    assert settings.scheduler.timezone == "Europe/Prague"


def test_prompt_requires_placeholder():
    with pytest.raises(ValidationError):
        PromptConfig(template="no placeholder here")


def test_prompt_rejects_doubled_token():
    with pytest.raises(ValidationError):
        PromptConfig(template="prefix {{weather_json}} suffix")


def test_prompt_accepts_single_token_with_unrelated_double_braces():
    template = "css: .a {{ color: red }} data: {weather_json}"
    config = PromptConfig(template=template)
    assert config.template == template


def test_prompt_substitution_preserves_literal_braces():
    template = "keep {{these}} and { that } but inject {weather_json}"
    rendered = template.replace("{weather_json}", '{"t": 1}')
    assert rendered == 'keep {{these}} and { that } but inject {"t": 1}'
