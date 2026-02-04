import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, is_dataclass
from typing import Self, TypeVar, cast


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
    board: list[list[str | None]]
    player: str
    winner: str | None


@dataclass(frozen=True)
class MoveRequested(Event):
    player: str
    row: int
    col: int


@dataclass(frozen=True)
class EnableInput(Event):
    player: str


@dataclass(frozen=True)
class InvalidMove(Event):
    error_msg: str
    player: str
    row: int
    col: int


@dataclass(frozen=True)
class StartTurn(Event):
    player: str


@dataclass(frozen=True)
class BoardRequested(Event):
    player: str


@dataclass(frozen=True)
class BoardProvided(Event):
    player: str
    board: list[list[str | None]]


E = TypeVar("E", bound=Event)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Callable[[Event], None]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:  # noqa: D102
        with self._lock:
            self._handlers.setdefault(event_type, []).append(cast("Callable[[Event], None]", handler))

    def publish(self, event: Event) -> None:  # noqa: D102
        with self._lock:
            handlers = self._handlers.get(type(event), []).copy()
        for handler in handlers:
            handler(event)  # don't catch here, let exceptions propagate, this is just a communication layer
