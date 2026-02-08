from typing import Any, Dict, List, Optional

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from ..ai.normalizer import HtmlNormalizer
from ..config import Settings
from ..state import StateService

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
        self.normalizer = HtmlNormalizer()
        self.active_connections: List[WebSocket] = []

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

    async def send_to_client(self, message: Optional[Dict[str, Any]], websocket: WebSocket) -> None:
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

    async def broadcast(self, message: Optional[Dict[str, Any]]) -> None:
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

    def make_config_info_message(self) -> Dict[str, Any]:
        return {
            "type": "config_info",
            "prompt_template": self.settings.prompt.template,
            "models": self.settings.get_enabled_ai_model_names(),
        }

    def make_weather_message(self) -> Optional[Dict[str, Any]]:
        if self.state_service.current_weather is None:
            return None

        return {
            "type": "weather_data",
            "timestamp": self.state_service.current_timestamp,
            "weather": self.state_service.current_weather,
        }

    def make_visualization_message(self, model_name: str) -> Optional[Dict[str, Any]]:
        raw_html = self.state_service.current_visualizations.get(model_name)

        # Clean up the AI output
        html = None
        if raw_html is not None:
            html = self.normalizer.normalize(raw_html)

        status = self.state_service.visualization_status.get(model_name, "up_to_date")

        return {
            "type": "visualization_update",
            "model_name": model_name,
            "html": html,
            "raw_html": raw_html,
            "status": status,
        }
