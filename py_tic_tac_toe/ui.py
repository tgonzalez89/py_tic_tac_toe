from abc import ABC, abstractmethod

from py_tic_tac_toe.exception import InvalidMoveError
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

    def _apply_move(self, row: int, col: int) -> None:
        # Disable own input immediately.
        # Prevents sending multiple moves.
        # This might not be strictly necessary because we're using a synchronous callback system,
        # but if the architecture changes in the future, this will prevent a potential bug.
        self._disable_input()
        try:
            self._game_engine.apply_move(row, col)
        except InvalidMoveError as e:
            self.enable_input()
            self._on_input_error(e)

    def enable_input(self) -> None:
        if not self._running:
            return
        self._input_enabled = True

    def _disable_input(self) -> None:
        self._input_enabled = False

    def on_board_updated(self) -> None:
        if not self._running:
            return
        # Disable input afterwards, when this function gets called by back by the game engine.
        # This prevents a bug when multiple UIs are running in network mode.
        # _apply_move only disables input for the UI that made the move, but on_board_updated
        # is called for all UIs after a successful move.
        # This also prevents a potential bug when an AI player is making a move and
        # the human player's input is still enabled.
        # This will not occur with a synchronous callback system, but if the architecture changes in the future,
        # this will prevent a potential bug.
        self._disable_input()
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
    def _on_input_error(self, exception: Exception) -> None:
        pass
