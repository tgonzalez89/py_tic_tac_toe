import random
from abc import ABC, abstractmethod
from collections.abc import Callable

from py_tic_tac_toe.board import Move, PlayerSymbol
from py_tic_tac_toe.exception import LogicError
from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player


class AiPlayer(Player, ABC):
    def __init__(self, symbol: PlayerSymbol, game: Game) -> None:
        super().__init__(symbol, game)
        self._apply_move_cb: Callable[[int, int], bool] = lambda _row, _col: True

    def set_apply_move_cb(self, callback: Callable[[int, int], bool]) -> None:
        self._apply_move_cb = callback

    def start_turn(self) -> None:
        row, col = self._find_move()
        self._apply_move_cb(row, col)

    def apply_move(self, row: int, col: int) -> bool:
        self._game.apply_move(Move(self._symbol, row, col))
        return True

    @abstractmethod
    def _find_move(self) -> tuple[int, int]:
        pass


class RandomAiPlayer(AiPlayer):
    def _find_move(self) -> tuple[int, int]:
        available_positions = self._game.board.get_available_positions()
        if not available_positions:
            raise LogicError("No available moves")
        return random.choice(available_positions)


class HardAiPlayer(AiPlayer):
    def _find_move(self) -> tuple[int, int]:
        # Placeholder for a more complex AI algorithm (e.g., Minimax)
        available_positions = self._game.board.get_available_positions()
        if not available_positions:
            raise LogicError("No available moves")
        return random.choice(available_positions)
