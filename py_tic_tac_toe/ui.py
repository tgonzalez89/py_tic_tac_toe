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

    def _queue_move(self, row: int, col: int) -> None:
        if not self._input_enabled or not self._running:
            return
        # Disable own input immediately.
        # Prevents sending multiple moves.
        self._disable_input()
        self._game_engine.queue_move(row, col)

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
        # This will not occur with a synchronous callback system, but for an asynchronous system,
        # this will prevent a potential bug.
        self._disable_input()
        self._render_board()
        winner = self._game_engine.game.board.get_winner()
        if winner:
            self._show_end_message(f"Winner: {winner}")
        elif self._game_engine.game.board.is_full():
            self._show_end_message("It's a draw")

    def on_error(self, _exception: Exception) -> None:
        if not self._running:
            return
        self.enable_input()

    @abstractmethod
    def _render_board(self) -> None:
        pass

    @abstractmethod
    def _show_end_message(self, msg: str) -> None:
        pass
