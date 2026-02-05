import atexit
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, is_dataclass
from queue import Empty, Queue
from typing import Self, TypeVar, cast

from py_tic_tac_toe.game.board_utils import PlayerSymbol


class Event:
    def to_dict(self) -> dict[str, object]:  # noqa: D102
        if not is_dataclass(self):
            raise TypeError("Expected a dataclass instance")

        data = asdict(self)
        data["type"] = self.__class__.__name__
        return data

    @classmethod
    def to_instance(cls, data: dict[str, object]) -> Self:  # noqa: D102
        if not is_dataclass(cls):
            raise TypeError("Expected a dataclass type")

        actual_type = data.get("type")
        expected_type = cls.__name__
        if actual_type != expected_type:
            msg = f"Type mismatch: expected '{expected_type}', got '{actual_type}'"
            raise ValueError(msg)

        field_names = {f.name for f in fields(cls)}
        missing_fields = field_names - set(data.keys())
        if missing_fields:
            msg = f"Missing required fields: {missing_fields}"
            raise ValueError(msg)
        filtered = {k: v for k, v in data.items() if k in field_names and k != "type"}
        return cls(**filtered)


@dataclass(frozen=True)
class StateUpdated(Event):
    player: PlayerSymbol
    board: list[list[PlayerSymbol | None]]


@dataclass(frozen=True)
class MoveRequested(Event):
    player: PlayerSymbol
    row: int
    col: int


@dataclass(frozen=True)
class EnableInput(Event):
    player: PlayerSymbol


@dataclass(frozen=True)
class InvalidMove(Event):
    player: PlayerSymbol
    row: int
    col: int
    error_msg: str


@dataclass(frozen=True)
class InputError(Event):
    player: PlayerSymbol
    error_msg: str


@dataclass(frozen=True)
class StartTurn(Event):
    player: PlayerSymbol


@dataclass(frozen=True)
class BoardRequested(Event):
    player: PlayerSymbol


@dataclass(frozen=True)
class BoardProvided(Event):
    player: PlayerSymbol
    board: list[list[PlayerSymbol | None]]


@dataclass(frozen=True)
class NetworkMessageSent(Event):
    player: PlayerSymbol
    message: dict[str, object]


@dataclass(frozen=True)
class AiThinkingComplete(Event):
    player: PlayerSymbol
    row: int
    col: int


E = TypeVar("E", bound=Event)


class EventBus:
    def __init__(self, *, use_async: bool = False) -> None:
        self._handlers: dict[type[Event], list[Callable[[Event], None]]] = {}
        self._handlers_lock = threading.RLock()
        self._use_async = use_async
        self._async_queue: Queue[Event] = Queue()
        self._async_running = False
        self._async_thread: threading.Thread | None = None
        atexit.register(self.close)  # Ensure cleanup on exit
        self._start_async()

    def _start_async(self) -> None:
        """Start the background thread that processes async events."""
        if not self._use_async:
            return
        self._async_thread = threading.Thread(target=self._process_async_queue, daemon=True)
        self._async_thread.start()

    def _process_async_queue(self) -> None:
        """Background thread: processes queued events one by one."""
        self._async_running = True
        while self._async_running:
            try:
                event = self._async_queue.get(timeout=0.1)
                with self._handlers_lock:
                    handlers = self._handlers.get(type(event), []).copy()
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception:  # noqa: TRY203
                        # Exceptions from handlers don't stop queue processing
                        raise
            except Empty:
                continue

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:  # noqa: D102
        with self._handlers_lock:
            self._handlers.setdefault(event_type, []).append(cast("Callable[[Event], None]", handler))

    def unsubscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:  # noqa: D102
        with self._handlers_lock:
            handlers = self._handlers.get(event_type)
            if not handlers:
                return
            try:
                handlers.remove(cast("Callable[[Event], None]", handler))
            except ValueError:
                return
            if not handlers:
                self._handlers.pop(event_type, None)

    def publish(self, event: Event) -> None:
        """Publish event synchronously (immediate delivery, blocking)."""
        with self._handlers_lock:
            handlers = self._handlers.get(type(event), []).copy()
        for handler in handlers:
            handler(event)

    def publish_async(self, event: Event) -> None:
        """Publish event asynchronously (queued for background thread processing)."""
        if not self._use_async:
            msg = "publish_async() requires EventBus initialized with use_async=True"
            raise RuntimeError(msg)
        self._async_queue.put(event)

    def _stop_async(self) -> None:
        """Stop the async processor thread (for graceful shutdown)."""
        if self._async_running:
            self._async_running = False
            if self._async_thread:
                self._async_thread.join(timeout=1.0)

    def close(self) -> None:  # noqa: D102
        self._stop_async()
        self._handlers.clear()
