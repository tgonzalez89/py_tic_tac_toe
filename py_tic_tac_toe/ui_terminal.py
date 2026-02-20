# ruff: noqa: T201

from py_tic_tac_toe.board import BOARD_SIZE
from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.ui import Ui


class TerminalUi(Ui):
    def __init__(self, game_engine: GameEngine) -> None:
        super().__init__(game_engine)

    def run(self) -> None:
        super().run()
        while self._running:
            self._get_input()
        print("Terminal UI stopped", flush=True)

    def _stop(self) -> None:
        print("Press Enter to exit", end="", flush=True)
        super()._stop()

    def enable_input(self) -> None:
        super().enable_input()
        if not self._running:
            return
        self._ask_for_move()

    def _ask_for_move(self) -> None:
        max_move = BOARD_SIZE * BOARD_SIZE
        print(f"Player {self._game_engine.current_player.symbol}'s move (1-{max_move}): ", end="", flush=True)

    def _get_input(self) -> None:
        try:
            input_str = input()
        except (KeyboardInterrupt, EOFError):
            super()._stop()
            return

        if input_str == "exit":
            super()._stop()

        if not self._input_enabled or not self._running:
            return

        try:
            board_position = int(input_str)
        except ValueError:
            self._on_input_error(ValueError("Not an integer"))
            self._ask_for_move()
            return
        else:
            max_move = BOARD_SIZE * BOARD_SIZE
            if not (1 <= board_position <= max_move):
                self._on_input_error(ValueError(f"Not between 1 and {max_move}"))
                self._ask_for_move()
                return

            index = board_position - 1
            row, col = divmod(index, BOARD_SIZE)

            self._queue_move(row, col)
            if not self._running:
                input()

    def _render_board(self) -> None:
        board = self._game_engine.game.board.board

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
        print(f"\n{output}\n", flush=True)

    def _show_end_message(self, msg: str) -> None:
        print(f"{msg}", flush=True)
        self._stop()

    def _on_input_error(self, exception: Exception) -> None:
        if not self._running:
            return
        print(str(exception), flush=True)

    def _on_other_error(self, exception: Exception) -> None:
        if not self._running:
            return
        print(str(exception), flush=True)
