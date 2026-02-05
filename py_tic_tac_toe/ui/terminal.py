# ruff: noqa: T201

import sys
import threading

from py_tic_tac_toe.event_bus.event_bus import EnableInput, EventBus, InvalidMove, MoveRequested, StateUpdated
from py_tic_tac_toe.game.board_utils import BOARD_SIZE, PlayerSymbol, get_winner, is_board_full
from py_tic_tac_toe.ui.ui import Ui


class TerminalUi(Ui):
    def __init__(self, event_bus: EventBus) -> None:
        super().__init__(event_bus)

        self._current_player: PlayerSymbol
        self._game_running = False
        self._number_typed = threading.Event()
        self._input_enabled = False

    def start(self) -> None:  # noqa: D102
        self._game_running = True
        self._number_typed.set()
        self._started = True
        self._input_loop()

    def _input_loop(self) -> None:
        while True:
            self._get_input()

    def _enable_input(self, event: EnableInput) -> None:
        self._current_player = event.player
        self._input_enabled = True
        self._ask_for_move()

    def _disable_input(self) -> None:
        self._input_enabled = False

    def _get_input(self) -> None:
        board_position = None
        while True:
            try:
                input_str = input()
            except (KeyboardInterrupt, EOFError):
                sys.exit()

            if not self._game_running:
                sys.exit()

            if input_str == "exit":
                sys.exit()

            if not self._input_enabled:
                break

            try:
                board_position = int(input_str)
            except ValueError:
                print("Not an integer")
                self._ask_for_move()
                continue
            else:
                max_move = BOARD_SIZE * BOARD_SIZE
                if board_position < 1 or board_position > max_move:
                    board_position = None
                    print(f"Not between 1 and {max_move}")
                    self._ask_for_move()
                    continue

                index = board_position - 1
                row, col = divmod(index, BOARD_SIZE)
                self._number_typed.set()

                self._disable_input()
                self._event_bus.publish(MoveRequested(self._current_player, row, col))
                break

    # -----------------------------
    # Rendering
    # -----------------------------

    def _render_board(self, board: list[list[PlayerSymbol | None]]) -> None:
        def _cell_value(index: int) -> str:
            row, col = divmod(index, len(board[0]))
            value = board[row][col]
            return value if value is not None else str(index + 1)

        rows = []
        for r in range(len(board)):
            start = r * len(board[0])
            row = " | ".join(_cell_value(start + i) for i in range(len(board[0])))
            rows.append(f" {row} ")

        separator = "\n-----------\n"
        output = separator.join(rows)

        if self._number_typed.is_set():
            self._number_typed.clear()
        else:
            print()
        print(f"\n{output}\n", flush=True)

    def _ask_for_move(self) -> None:
        max_move = BOARD_SIZE * BOARD_SIZE
        print(f"Player {self._current_player}'s move (1-{max_move}): ", end="", flush=True)

    # -----------------------------
    # Event handling
    # -----------------------------

    def _on_state_updated(self, event: StateUpdated) -> None:
        self._current_player = event.player

        self._render_board(event.board)

        winner = get_winner(event.board)
        if winner:
            self._show_end_message(f"Winner: {winner}")
        elif is_board_full(event.board):
            self._show_end_message("It's a draw")

    def _show_end_message(self, msg: str) -> None:
        self._game_running = False
        print(f"{msg}\nPress Enter to exit", flush=True)

    def _on_invalid_move(self, event: InvalidMove) -> None:
        print(event.error_msg)
        self._enable_input(EnableInput(event.player))
