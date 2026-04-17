"""Kafka startup retry, transient-error detection, and graceful shutdown helpers."""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

try:
    from aiokafka.errors import (
        BrokerNotAvailableError,
        KafkaConnectionError,
        KafkaTimeoutError,
        LeaderNotAvailableError,
        NotLeaderForPartitionError,
        RequestTimedOutError,
    )

    TRANSIENT_EXC_TYPES: tuple[type[BaseException], ...] = (
        BrokerNotAvailableError,
        KafkaConnectionError,
        KafkaTimeoutError,
        LeaderNotAvailableError,
        NotLeaderForPartitionError,
        RequestTimedOutError,
        ConnectionError,
        OSError,
        asyncio.TimeoutError,
    )
except ImportError:  # pragma: no cover
    TRANSIENT_EXC_TYPES = (
        ConnectionError,
        OSError,
        asyncio.TimeoutError,
    )


def startup_max_attempts() -> int:
    return max(1, int(os.environ.get("KAFKA_STARTUP_MAX_ATTEMPTS", "30")))


def startup_backoff_seconds() -> float:
    return max(0.1, float(os.environ.get("KAFKA_STARTUP_BACKOFF_SECONDS", "5")))


def runtime_reconnect_backoff_seconds() -> float:
    return max(0.1, float(os.environ.get("KAFKA_RUNTIME_RECONNECT_BACKOFF_SECONDS", "5")))


def send_max_recovery_rounds() -> int:
    return max(1, int(os.environ.get("KAFKA_SEND_MAX_RECOVERY_ROUNDS", "5")))


def is_transient_kafka_error(exc: BaseException) -> bool:
    return isinstance(exc, TRANSIENT_EXC_TYPES)


async def safe_stop_client(client: Any) -> None:
    try:
        await client.stop()
    except Exception:
        pass


async def start_with_backoff(
    factory: Callable[[], T],
    *,
    attempts: int | None = None,
    backoff_s: float | None = None,
    label: str = "kafka client",
) -> T:
    """Create a client from ``factory``, call ``await client.start()``, retry on transient errors."""
    attempts = startup_max_attempts() if attempts is None else attempts
    backoff_s = startup_backoff_seconds() if backoff_s is None else backoff_s
    last_exc: BaseException | None = None
    for i in range(attempts):
        client = factory()
        try:
            await client.start()
            return client
        except BaseException as exc:
            last_exc = exc
            await safe_stop_client(client)
            if not is_transient_kafka_error(exc):
                raise
            if i == attempts - 1:
                break
            print(f"{label}: Kafka not ready ({exc}), retrying in {backoff_s}s… ({i + 1}/{attempts})")
            await asyncio.sleep(backoff_s)
    assert last_exc is not None
    raise last_exc


def attach_shutdown_handlers(stop_event: asyncio.Event) -> None:
    """Set ``stop_event`` on SIGINT / SIGTERM where the event loop supports it."""

    loop = asyncio.get_running_loop()

    def set_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, set_stop)
        except (NotImplementedError, RuntimeError, ValueError):
            if sig == signal.SIGINT:

                def handler(signum: int, frame: Any) -> None:
                    set_stop()

                signal.signal(signal.SIGINT, handler)


async def send_with_producer_recovery(
    producer_cell: list[Any],
    producer_factory: Callable[[], Any],
    *,
    topic: str,
    value: bytes,
    max_rounds: int | None = None,
    startup_attempts: int | None = None,
    startup_backoff: float | None = None,
) -> None:
    """Send one message; on transient failure stop producer, recreate via ``start_with_backoff``, retry."""
    rounds = send_max_recovery_rounds() if max_rounds is None else max_rounds
    for r in range(rounds):
        try:
            await producer_cell[0].send_and_wait(topic, value)
            return
        except BaseException as exc:
            if not is_transient_kafka_error(exc):
                raise
            if r == rounds - 1:
                raise
            await safe_stop_client(producer_cell[0])
            producer_cell[0] = await start_with_backoff(
                producer_factory,
                attempts=startup_attempts,
                backoff_s=startup_backoff,
                label="kafka producer (recover)",
            )


async def recv_websocket_or_shutdown(
    socket: Any,
    *,
    timeout_seconds: float,
    shutdown_event: asyncio.Event,
) -> Any | None:
    """Wait for one WebSocket frame or shutdown. Returns ``None`` if shutdown won the race."""
    recv_task = asyncio.create_task(asyncio.wait_for(socket.recv(), timeout=timeout_seconds))
    stop_task = asyncio.create_task(shutdown_event.wait())
    try:
        done, pending = await asyncio.wait({recv_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        for t in pending:
            try:
                await t
            except asyncio.CancelledError:
                pass

        if shutdown_event.is_set():
            if not recv_task.done():
                recv_task.cancel()
                try:
                    await recv_task
                except asyncio.CancelledError:
                    pass
            return None

        if recv_task.done() and not recv_task.cancelled():
            exc = recv_task.exception()
            if exc is not None:
                raise exc
            return recv_task.result()

        return None
    finally:
        for t in (recv_task, stop_task):
            if not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
