from abc import ABC, abstractmethod

from py_tic_tac_toe.event_bus.event_bus import EventBus, StartTurn


class Player(ABC):
    def __init__(self, event_bus: EventBus, symbol: str) -> None:
        self._symbol = symbol
        self._event_bus = event_bus
        self._event_bus.subscribe(StartTurn, self._on_start_turn)

    @abstractmethod
    def _on_start_turn(self, event: StartTurn) -> None:
        pass
