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

    @abstractmethod
    def apply_move(self, row: int, col: int) -> bool:
        pass
