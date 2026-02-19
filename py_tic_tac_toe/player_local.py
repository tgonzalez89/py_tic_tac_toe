from collections.abc import Callable

from py_tic_tac_toe.board import Move, PlayerSymbol
from py_tic_tac_toe.exception import InvalidMoveError
from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player


class LocalPlayer(Player):
    def __init__(self, symbol: PlayerSymbol, game: Game) -> None:
        super().__init__(symbol, game)
        self._enable_input_cbs: list[Callable[[], None]]
        self._input_error_cbs: list[Callable[[Exception], None]]

    def add_enable_input_cb(self, callback: Callable[[], None]) -> None:
        if not hasattr(self, "_enable_input_cbs"):
            self._enable_input_cbs = []
        self._enable_input_cbs.append(callback)

    def add_input_error_cb(self, callback: Callable[[Exception], None]) -> None:
        if not hasattr(self, "_input_error_cbs"):
            self._input_error_cbs = []
        self._input_error_cbs.append(callback)

    def start_turn(self) -> None:
        for callback in list(self._enable_input_cbs):
            callback()

    def apply_move(self, row: int, col: int) -> bool:
        try:
            self._game.apply_move(Move(self._symbol, row, col))
        except InvalidMoveError as e:
            for callback in list(self._input_error_cbs):
                callback(e)
            return False
        return True
