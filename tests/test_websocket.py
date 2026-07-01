"""Tests for the WebSocket message builders."""

from aiweather.state import StateService
from aiweather.visualization import HtmlNormalizer, Visualization, VisualizationStatus
from aiweather.websocket import ConnectionManager
from tests.conftest import FakeWebSocket, make_settings


def make_manager(state: StateService) -> ConnectionManager:
    return ConnectionManager(make_settings(), state)


def test_visualization_message_shape_and_status_string():
    state = StateService()
    state.update_visualization("Model One", Visualization.from_raw("```html\n<h1>Hi</h1>\n```", HtmlNormalizer()))
    state.mark_generating("Model One")
    msg = make_manager(state).make_visualization_message("Model One")

    assert msg == {
        "type": "visualization_update",
        "model_name": "Model One",
        "html": "<h1>Hi</h1>",
        "raw_html": "```html\n<h1>Hi</h1>\n```",
        "status": "generating",
    }
    assert isinstance(msg["status"], str) and not isinstance(msg["status"], VisualizationStatus)


def test_visualization_message_absent_model_html_null():
    state = StateService()
    msg = make_manager(state).make_visualization_message("Missing")
    assert msg["html"] is None
    assert msg["raw_html"] is None
    assert msg["status"] == "up_to_date"


def test_weather_message_none_when_no_weather():
    state = StateService()
    assert make_manager(state).make_weather_message() is None


def test_weather_message_timestamp_is_offset_free():
    state = StateService()
    state.update_weather({"temp": 1})
    state.update_timestamp("2026-07-01T12:00:00+02:00")
    msg = make_manager(state).make_weather_message()
    assert msg["type"] == "weather_data"
    assert set(msg) == {"type", "timestamp", "weather"}
    assert msg["timestamp"] == "2026-07-01T12:00:00"


def test_weather_message_tolerates_unparseable_timestamp():
    state = StateService()
    state.update_weather({"temp": 1})
    state.update_timestamp("15-14")
    msg = make_manager(state).make_weather_message()
    assert msg["timestamp"] == "15-14"


async def test_send_to_client_prunes_on_failure():
    manager = make_manager(StateService())
    ws = FakeWebSocket(fail=True)
    manager.active_connections.append(ws)
    await manager.send_to_client({"type": "x"}, ws)
    assert ws not in manager.active_connections


async def test_broadcast_prunes_failing_keeps_healthy():
    manager = make_manager(StateService())
    healthy = FakeWebSocket()
    dead = FakeWebSocket(fail=True)
    manager.active_connections.extend([healthy, dead])
    await manager.broadcast({"type": "weather_data"})
    assert manager.active_connections == [healthy]
    assert healthy.sent == [{"type": "weather_data"}]


async def test_handle_disconnects_on_receive_error():
    manager = make_manager(StateService())

    class DisconnectingWS(FakeWebSocket):
        async def accept(self):
            return None

        async def receive(self):
            from fastapi import WebSocketDisconnect

            raise WebSocketDisconnect()

    ws = DisconnectingWS()
    await manager.handle(ws)
    assert ws not in manager.active_connections
