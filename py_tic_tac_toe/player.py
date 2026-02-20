from abc import ABC, abstractmethod

from py_tic_tac_toe.board import PlayerSymbol


class Player(ABC):
    def __init__(self, symbol: PlayerSymbol) -> None:
        self._symbol = symbol

    @property
    def symbol(self) -> PlayerSymbol:
        return self._symbol

    @abstractmethod
    def start_turn(self) -> None:
        pass

    def on_move_applied(self, row: int, col: int) -> None:  # noqa: B027
        pass
