from collections.abc import Callable

from py_tic_tac_toe.board import PlayerSymbol
from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player


class LocalPlayer(Player):
    def __init__(self, symbol: PlayerSymbol, game: Game) -> None:
        super().__init__(symbol, game)
        self._enable_input_cbs: list[Callable[[], None]]

    def add_enable_input_cb(self, callback: Callable[[], None]) -> None:
        if not hasattr(self, "_enable_input_cbs"):
            self._enable_input_cbs = []
        self._enable_input_cbs.append(callback)

    def start_turn(self) -> None:
        for callback in list(self._enable_input_cbs):
            callback()
