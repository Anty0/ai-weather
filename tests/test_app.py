"""Wired-app integration tests over create_app via TestClient."""

import httpx
import pytest
from fastapi.testclient import TestClient

from aiweather.main import create_app
from tests.conftest import FakeProvider, make_settings


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"current": {"temp": 12}}


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        return _FakeResponse()


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    """Keep the startup refresh hermetic; never hit the real OpenWeather API."""
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)


def build_client(*, provider=None, settings=None):
    settings = settings or make_settings()
    provider = provider or FakeProvider()
    return TestClient(create_app(settings=settings, provider_factory=lambda s: {"ollama": provider}))


def test_root_serves_index_html():
    with build_client() as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "<!DOCTYPE html>" in resp.text or "<html" in resp.text


def test_root_served_from_arbitrary_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with build_client() as client:
        assert client.get("/").status_code == 200


def test_health_is_cheap_ok():
    with build_client() as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_200_when_available():
    with build_client(provider=FakeProvider(available=True)) as client:
        resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True


def test_ready_503_when_unavailable():
    with build_client(provider=FakeProvider(available=False)) as client:
        resp = client.get("/ready")
    assert resp.status_code == 503
    assert resp.json()["ready"] is False


def test_ready_503_when_probe_raises():
    with build_client(provider=FakeProvider(available_error=RuntimeError("down"))) as client:
        resp = client.get("/ready")
    assert resp.status_code == 503


def test_ready_503_when_probe_times_out():
    settings = make_settings(readiness_probe_timeout_seconds=0.05)
    provider = FakeProvider(available_sleep=1.0)
    with build_client(provider=provider, settings=settings) as client:
        resp = client.get("/ready")
    assert resp.status_code == 503


def test_ready_503_when_no_providers():
    app = create_app(settings=make_settings(), provider_factory=lambda s: {})
    with TestClient(app) as client:
        resp = client.get("/ready")
    assert resp.status_code == 503
    assert resp.json()["ready"] is False


def test_lifespan_starts_when_probe_raises():
    with build_client(provider=FakeProvider(available_error=RuntimeError("boom"))) as client:
        assert client.get("/health").status_code == 200


def test_lifespan_starts_when_probe_hangs():
    settings = make_settings(readiness_probe_timeout_seconds=0.05)
    provider = FakeProvider(available_sleep=1.0)
    with build_client(provider=provider, settings=settings) as client:
        assert client.get("/health").status_code == 200


def test_lifespan_starts_when_archive_load_fails(monkeypatch):
    from aiweather.scheduler import RefreshService

    async def boom(self):
        raise RuntimeError("corrupt archive")

    monkeypatch.setattr(RefreshService, "load_initial_state", boom)
    with build_client() as client:
        assert client.get("/health").status_code == 200


def test_websocket_sends_initial_config():
    with build_client() as client:
        with client.websocket_connect("/ws") as ws:
            first = ws.receive_json()
    assert first["type"] == "config_info"
    assert first["models"] == ["Model One"]
