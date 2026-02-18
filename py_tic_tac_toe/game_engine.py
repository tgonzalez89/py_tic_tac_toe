from collections.abc import Callable

from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player


class GameEngine:
    def __init__(self) -> None:
        self._game = Game()
        self._board_updated_cbs: list[Callable[[], None]] = []

    @property
    def game(self) -> Game:
        return self._game

    @property
    def current_player(self) -> Player:
        return self._player1 if self._game.current_player == self._player1.symbol else self._player2

    def set_players(self, player1: Player, player2: Player) -> None:
        self._player1 = player1
        self._player2 = player2

    def add_board_updated_cb(self, callback: Callable[[], None]) -> None:
        self._board_updated_cbs.append(callback)

    def start(self) -> None:
        self._notify_board_updated()
        self._start_next_turn()

    def apply_move(self, row: int, col: int) -> bool:
        move_applied = self.current_player.apply_move(row, col)
        if move_applied:
            self._notify_board_updated()
        self._start_next_turn()
        return move_applied

    def _notify_board_updated(self) -> None:
        for callback in list(self._board_updated_cbs):
            callback()

    def _start_next_turn(self) -> None:
        if self._game.board.is_full() or self._game.board.get_winner():
            return
        self.current_player.start_turn()
