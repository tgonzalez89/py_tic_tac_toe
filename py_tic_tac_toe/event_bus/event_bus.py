from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar, cast


class Event:
    pass


@dataclass
class StateUpdated(Event):
    board: list[list[str | None]]
    current_player: str
    winner: str | None


@dataclass
class MoveRequested(Event):
    player: str
    row: int
    col: int


@dataclass
class EnableInput(Event):
    player: str


@dataclass
class InvalidMove(Event):
    msg: str


@dataclass
class StartTurn(Event):
    board: list[list[str | None]]
    current_player: str


E = TypeVar("E", bound=Event)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Callable[[Event], None]]] = {}

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:  # noqa: D102
        self._handlers.setdefault(event_type, []).append(cast("Callable[[Event], None]", handler))

    def publish(self, event: Event) -> None:  # noqa: D102
        for handler in self._handlers.get(type(event), []):
            handler(event)
