# ruff: noqa: T201

import os
import threading

from py_tic_tac_toe.game_engine.event import EnableInput, EventBus, InvalidMove, MoveRequested, StateUpdated
from py_tic_tac_toe.ui.ui import Ui


class TerminalUi(Ui):
    def __init__(self, event_bus: EventBus) -> None:
        super().__init__(event_bus)

        self.current_player: str
        self.game_running = False
        self.number_typed = threading.Event()

    def start(self) -> None:  # noqa: D102
        self.game_running = True
        self.number_typed.set()
        self._started = True
        self._input_loop()

    def _input_loop(self) -> None:
        while True:
            self._get_input()

    def _enable_input(self, event: EnableInput) -> None:
        self.current_player = event.player

    def _get_input(self) -> None:
        digit = None
        while True:
            try:
                input_str = input()
            except BaseException:  # noqa: BLE001
                os._exit(0)

            if not self.game_running:
                os._exit(0)

            if input_str == "exit":
                os._exit(0)

            try:
                digit = int(input_str)
            except ValueError:
                print("Not an integer")
                self._ask_for_move(self.current_player)
            else:
                if digit < 1 or digit > 9:  # noqa: PLR2004
                    digit = None
                    print("Not between 1 and 9")
                    self._ask_for_move(self.current_player)
                    continue
                digit -= 1
                row, col = divmod(digit, 3)
                self.number_typed.set()
                try:
                    self.event_bus.publish(MoveRequested(self.current_player, row, col))
                    break
                except ValueError as e:
                    print(e)
                    self._ask_for_move(self.current_player)

    # -----------------------------
    # Rendering
    # -----------------------------

    def _render_board(self, board: list[list[str | None]]) -> None:
        def _cell_value(index: int) -> str:
            row, col = divmod(index, 3)
            value = board[row][col]
            return value if value is not None else str(index + 1)

        rows = []
        for r in range(3):
            start = r * 3
            row = " | ".join(_cell_value(start + i) for i in range(3))
            rows.append(f" {row} ")

        separator = "\n-----------\n"
        output = separator.join(rows)

        if self.number_typed.is_set():
            self.number_typed.clear()
        else:
            print()
        print(f"\n{output}\n", flush=True)

    def _ask_for_move(self, current_player: str) -> None:
        print(f"Player {current_player}'s move (1-9): ", end="", flush=True)

    # -----------------------------
    # Event handling
    # -----------------------------

    def _on_state_updated(self, event: StateUpdated) -> None:
        self._render_board(event.board)

        if event.winner:
            self._show_end_message(f"Winner: {event.winner}")
        elif all(all(cell is not None for cell in row) for row in event.board):
            self._show_end_message("It's a draw")
        else:
            self._ask_for_move(event.current_player)

    def _show_end_message(self, msg: str) -> None:
        self.game_running = False
        print(f"{msg}\nPress Enter to exit", flush=True)

    def _on_error(self, event: InvalidMove) -> None:
        pass
