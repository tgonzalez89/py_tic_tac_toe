# ruff: noqa: T201

import os
import threading

from py_tic_tac_toe.engine.game_engine import GameEngine, MoveRequested, StateUpdated


class TerminalUI:
    def __init__(self, game_engine: GameEngine) -> None:
        self.game_engine = game_engine
        self.current_player = "X"
        self.number_typed = threading.Event()
        self.game_engine.subscribe(StateUpdated, self._on_state_updated)
        self.game_engine.subscribe(ValueError, self._on_error)

    def start(self) -> None:  # noqa: D102
        self.number_typed.set()
        self._render_board(self.game_engine.game.board)
        self._ask_for_move()
        self._input_loop()

    def _input_loop(self) -> None:
        while True:
            digit = None
            while digit is None:
                try:
                    raw = input()
                except BaseException:  # noqa: BLE001
                    os._exit(0)
                if raw == "exit":
                    os._exit(0)
                try:
                    digit = int(raw)
                except ValueError:
                    self._on_error(ValueError("Not an integer"))
                else:
                    if digit < 1 or digit > 9:  # noqa: PLR2004
                        digit = None
                        self._on_error(ValueError("Not between 1 and 9"))
                        continue
                    digit -= 1
                    r = digit // 3
                    c = digit % 3
                    self.number_typed.set()
                    self.game_engine.on_move_requested(MoveRequested(self.current_player, r, c))

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

        if not self.number_typed.is_set():
            print()
        else:
            self.number_typed.clear()
        print(f"\n{output}\n")

    def _ask_for_move(self) -> None:
        print(f"Player {self.current_player}'s move (1-9): ", end="", flush=True)

    def _on_state_updated(self, event: StateUpdated) -> None:
        self.current_player = event.current_player
        self._render_board(event.board)
        if event.winner:
            print("Winner:", event.winner, flush=True)
            os._exit(0)
        elif all(all(cell is not None for cell in row) for row in event.board):
            print("It's a draw", flush=True)
            os._exit(0)
        self._ask_for_move()

    def _on_error(self, event: ValueError) -> None:
        print(event)
        self._ask_for_move()
