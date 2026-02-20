from abc import ABC, abstractmethod

from py_tic_tac_toe.board import PlayerSymbol
from py_tic_tac_toe.game import Game


class Player(ABC):
    def __init__(self, symbol: PlayerSymbol, game: Game) -> None:
        self._symbol = symbol
        self._game = game

    @property
    def symbol(self) -> PlayerSymbol:
        return self._symbol

    @abstractmethod
    def start_turn(self) -> None:
        pass

    def on_move_applied(self, row: int, col: int) -> None:  # noqa: B027
        pass
