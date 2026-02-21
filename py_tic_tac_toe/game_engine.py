import threading
from collections.abc import Callable

from py_tic_tac_toe.board import Move
from py_tic_tac_toe.exception import InvalidMoveError, NetworkError
from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player


class GameEngine:
    def __init__(self) -> None:
        self._game = Game()
        self._board_updated_cbs: list[Callable[[], None]] = []
        self._on_error_cbs: list[Callable[[Exception], None]] = []
        self._running = False
        self._game_thread: threading.Thread | None = None

    @property
    def game(self) -> Game:
        return self._game

    @property
    def current_player(self) -> Player:
        return self._player1 if self._game.current_player_symbol == self._player1.symbol else self._player2

    def set_players(self, player1: Player, player2: Player) -> None:
        self._player1 = player1
        self._player2 = player2

    def add_board_updated_cb(self, callback: Callable[[], None]) -> None:
        self._board_updated_cbs.append(callback)

    def add_on_error_cb(self, callback: Callable[[Exception], None]) -> None:
        self._on_error_cbs.append(callback)

    def start(self) -> None:
        """Start the game in manual mode. The caller must call tick() to advance the game."""
        self._notify_board_updated()
        self.current_player.start_turn()

    def start_game_loop(self) -> None:
        """Start the game with an automatic game loop running in a background thread."""
        self._running = True
        self._notify_board_updated()
        self.current_player.start_turn()
        self._game_thread = threading.Thread(target=self._game_loop, daemon=True)
        self._game_thread.start()

    def stop_game_loop(self) -> None:
        """Stop the automatic game loop."""
        self._running = False
        if self._game_thread:
            self._game_thread.join(timeout=1.0)
            self._game_thread = None

    def tick(self, *, block: bool = False, timeout: float | None = None) -> None:
        """Process one iteration of the game logic.

        Checks if the current player has a pending move, applies it if available,
        and starts the next player's turn. Call this repeatedly from a UI loop
        when using manual mode, or let start_game_loop() handle it automatically.
        """
        if self._game.board.is_game_over():
            return

        move = self.current_player.get_pending_move(block=block, timeout=timeout)
        if move is None:
            return

        # Apply the pending move with error handling.
        row, col = move
        try:
            self._game.apply_move(Move(self.current_player.symbol, row, col))
            self._notify_board_updated()
        except (InvalidMoveError, IndexError, NetworkError) as e:
            self._notify_on_error(e)
            return

        # Start next turn if game not over
        if self._game.board.is_game_over():
            return
        self.current_player.start_turn()

    def queue_move(self, row: int, col: int) -> None:
        """Submit a move from the UI or external source.

        This queues the move for the current player to be processed by the next tick().
        """
        self.current_player.queue_move(row, col)

    def _game_loop(self, tick_timeout: float | None = None) -> None:
        """Background thread that continuously calls tick() to drive the game forward."""
        while self._running and not self._game.board.is_game_over():
            self.tick(block=True, timeout=tick_timeout)
        self._running = False

    def _notify_board_updated(self) -> None:
        for callback in list(self._board_updated_cbs):
            callback()

    def _notify_on_error(self, exception: Exception) -> None:
        """Notify error callbacks when any error occurs."""
        for callback in list(self._on_error_cbs):
            callback(exception)
