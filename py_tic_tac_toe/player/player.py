from abc import ABC, abstractmethod

from py_tic_tac_toe.game_engine.event import EventBus, StartTurn


class Player(ABC):
    def __init__(self, event_bus: EventBus, symbol: str) -> None:
        self.symbol = symbol
        self.event_bus = event_bus
        self.event_bus.subscribe(StartTurn, self._on_start_turn)

    @abstractmethod
    def _on_start_turn(self, event: StartTurn) -> None:
        pass
