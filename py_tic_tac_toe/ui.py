from abc import ABC, abstractmethod

from py_tic_tac_toe.game_engine import GameEngine


class Ui(ABC):
    def __init__(self, game_engine: GameEngine) -> None:
        self._game_engine = game_engine
        self._running = False
        self._input_enabled = False

    @property
    def running(self) -> bool:
        return self._running

    def run(self) -> None:
        self._running = True

    def _stop(self) -> None:
        self._running = False

    def _apply_move(self, row: int, col: int) -> bool:
        self._disable_input()
        return self._game_engine.apply_move(row, col)

    def enable_input(self) -> None:
        if not self._running:
            return
        self._input_enabled = True

    def _disable_input(self) -> None:
        self._input_enabled = False

    def on_board_updated(self) -> None:
        if not self._running:
            return
        self._render_board()
        winner = self._game_engine.game.board.get_winner()
        if winner:
            self._show_end_message(f"Winner: {winner}")
        elif self._game_engine.game.board.is_full():
            self._show_end_message("It's a draw")

    @abstractmethod
    def _render_board(self) -> None:
        pass

    @abstractmethod
    def _show_end_message(self, message: str) -> None:
        pass

    @abstractmethod
    def on_input_error(self, exception: Exception) -> None:
        pass
