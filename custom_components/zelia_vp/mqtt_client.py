"""Direct MQTT client for a Zelia VP device broker."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable

import aiomqtt

_LOGGER = logging.getLogger(__name__)

# MQTT keepalive: how often the broker expects a PING if idle.
# Short keepalive (15s) ensures quick detection of network issues.
# The Zelia device broker supports this; TomTuT reference uses 15s.
MQTT_KEEPALIVE_SECONDS = 15

MessageCallback = Callable[[str, str], None]
ConnectionCallback = Callable[[bool], None]


class ZeliaMqttClient:
    """Async MQTT client with reconnect, bound to one device broker."""

    def __init__(
        self,
        host: str,
        port: int,
        device_id: str,
        on_message: MessageCallback,
        on_connection_change: ConnectionCallback | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._device_id = device_id
        self._on_message = on_message
        self._on_connection_change = on_connection_change
        self._client_id = f"ha-zelia-{device_id[-12:]}-{uuid.uuid4().hex[:8]}"
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._publish_client: aiomqtt.Client | None = None
        self.connected = False

    async def start(self) -> None:
        """Start the background listen loop."""
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(
            self._run(), name=f"zelia_mqtt_{self._device_id}"
        )

    async def stop(self) -> None:
        """Stop the client and cancel background tasks."""
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._publish_client = None
        self.connected = False

    async def publish(self, topic: str, payload: str) -> None:
        """Publish a message if connected."""
        client = self._publish_client
        if client is None or not self.connected:
            _LOGGER.warning(
                "Cannot publish %s = %s: MQTT client is not connected",
                topic,
                payload,
            )
            raise ConnectionError("MQTT client is not connected")
        await client.publish(topic, payload)
        _LOGGER.debug("Published %s = %s", topic, payload)

    async def _run(self) -> None:
        """Connect loop with exponential backoff. Context manager owns disconnect."""
        delay = 1.0
        while not self._stop.is_set():
            try:
                async with aiomqtt.Client(
                    hostname=self._host,
                    port=self._port,
                    identifier=self._client_id,
                    keepalive=MQTT_KEEPALIVE_SECONDS,
                ) as client:
                    self._publish_client = client
                    self.connected = True
                    if self._on_connection_change:
                        self._on_connection_change(True)
                    delay = 1.0
                    topic = f"{self._device_id}/#"
                    await client.subscribe(topic)
                    _LOGGER.info(
                        "Connected to Zelia MQTT %s:%s, subscribed to %s",
                        self._host,
                        self._port,
                        topic,
                    )
                    async for message in client.messages:
                        if self._stop.is_set():
                            break
                        payload = message.payload
                        if isinstance(payload, bytes):
                            text = payload.decode("utf-8", errors="replace")
                        else:
                            text = str(payload)
                        # Same event loop as HA (task created from setup).
                        self._on_message(str(message.topic), text)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 — reconnect on any MQTT error
                if self._stop.is_set():
                    break
                _LOGGER.warning(
                    "MQTT connection error on %s:%s (%s); retry in %.0fs",
                    self._host,
                    self._port,
                    err,
                    delay,
                )
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except TimeoutError:
                    pass
                delay = min(delay * 2, 60.0)
            finally:
                was_connected = self.connected
                self.connected = False
                self._publish_client = None
                if was_connected and self._on_connection_change:
                    self._on_connection_change(False)


async def validate_mqtt_connection(
    host: str,
    port: int,
    device_id: str | None = None,
    timeout: float = 5.0,
) -> str | None:
    """
    Try connecting to the broker.

    Connection success is enough for config flow (device may be quiet).
    If messages arrive for a zelix_ prefix, return that device_id.
    """
    seen: list[str] = []
    client_id = f"ha-zelia-validate-{uuid.uuid4().hex[:8]}"

    async with asyncio.timeout(timeout):
        async with aiomqtt.Client(
            hostname=host,
            port=port,
            identifier=client_id,
        ) as client:
            if device_id:
                await client.subscribe(f"{device_id}/#")
            else:
                await client.subscribe("zelix_#")
            try:
                async with asyncio.timeout(min(3.0, timeout)):
                    async for message in client.messages:
                        topic = str(message.topic)
                        prefix = topic.split("/", 1)[0]
                        if prefix.startswith("zelix_"):
                            seen.append(prefix)
                            if device_id is None or prefix == device_id:
                                return prefix
            except TimeoutError:
                return device_id

    return device_id if device_id else (seen[0] if seen else None)
