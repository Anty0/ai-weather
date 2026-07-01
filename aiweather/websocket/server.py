from datetime import datetime
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from ..config import Settings
from ..state import StateService
from ..visualization import VisualizationStatus

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self, settings: Settings, state_service: StateService) -> None:
        """Initialize connection manager.

        Args:
            settings: Application settings
            state_service: State service for reading current state
        """
        self.settings = settings
        self.state_service = state_service
        self.active_connections: list[WebSocket] = []

    async def handle(self, websocket: WebSocket) -> None:
        """Handle the WebSocket connection lifecycle."""
        await self.connect(websocket)

        try:
            # Keep the connection open
            while True:
                # Receive and ignore any messages (no client messages expected)
                message = await websocket.receive()
                logger.debug("websocket_received_message", client=websocket.client, message=message)

        except WebSocketDisconnect:
            self.disconnect(websocket)
        except RuntimeError:
            self.disconnect(websocket)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept connection and send initial state.

        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("client_connected", total=len(self.active_connections))

        # Send config info first
        await self.send_to_client(self.make_config_info_message(), websocket)

        # Send current weather data if available
        await self.send_to_client(self.make_weather_message(), websocket)

        # Send current visualizations if available
        for model_name in self.settings.get_enabled_ai_model_names():
            await self.send_to_client(self.make_visualization_message(model_name), websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect a client.

        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("client_disconnected", total=len(self.active_connections))

    async def send_to_client(self, message: dict[str, Any] | None, websocket: WebSocket) -> None:
        """Send a message to a specific client.

        Args:
            message: Message dictionary
            websocket: WebSocket connection
        """
        if message is None:
            # No message to send
            return

        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning("send_failed", error=str(e))
            self.disconnect(websocket)

    async def broadcast(self, message: dict[str, Any] | None) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: Message dictionary
        """
        if message is None:
            # No message to send
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                disconnected.append(connection)
                logger.warning("send_failed", client=connection.client, error=str(e))

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

        logger.info("broadcast_sent", recipients=len(self.active_connections), message=message["type"])

    async def broadcast_weather(self) -> None:
        """Broadcast weather update to all clients."""
        await self.broadcast(self.make_weather_message())

    async def broadcast_visualization(self, model_name: str) -> None:
        """Broadcast a single visualization update.

        Args:
            model_name: Name of the AI model
        """
        await self.broadcast(self.make_visualization_message(model_name))

    def make_config_info_message(self) -> dict[str, Any]:
        return {
            "type": "config_info",
            "prompt_template": self.settings.prompt.template,
            "models": self.settings.get_enabled_ai_model_names(),
        }

    def make_weather_message(self) -> dict[str, Any] | None:
        if self.state_service.current_weather is None:
            return None

        return {
            "type": "weather_data",
            "timestamp": self._wire_timestamp(self.state_service.current_timestamp),
            "weather": self.state_service.current_weather,
        }

    @staticmethod
    def _wire_timestamp(timestamp: str | None) -> str | None:
        """Emit the timestamp as offset-free local wall clock so the frontend renders
        the configured-tz hour identically for every viewer regardless of browser tz."""
        if timestamp is None:
            return None
        try:
            return datetime.fromisoformat(timestamp).replace(tzinfo=None).isoformat()
        except ValueError:
            return timestamp

    def make_visualization_message(self, model_name: str) -> dict[str, Any]:
        visualization = self.state_service.current_visualizations.get(model_name)
        status = self.state_service.visualization_status.get(model_name, VisualizationStatus.UP_TO_DATE)

        return {
            "type": "visualization_update",
            "model_name": model_name,
            "html": visualization.normalized if visualization is not None else None,
            "raw_html": visualization.raw if visualization is not None else None,
            "status": status.value,
        }
