import threading
import tkinter as tk
from functools import partial
from tkinter import messagebox
from typing import Final

from py_tic_tac_toe.board import BOARD_SIZE
from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.ui import Ui


class TkUi(Ui):
    TITLE: Final = "Tic-Tac-Toe (Pygame)"

    def __init__(self, game_engine: GameEngine) -> None:
        super().__init__(game_engine)
        self._buttons: list[tk.Button] = []

    def run(self) -> None:
        self._root = tk.Tk()
        self._root.title(self.TITLE)
        self._root.protocol("WM_DELETE_WINDOW", self._stop)
        self._build_grid()
        super().run()
        self._root.mainloop()

    def _stop(self) -> None:
        self._root.after(0, self._root.quit)
        super()._stop()

    def enable_input(self) -> None:
        super().enable_input()
        if not self._running:
            return
        self._root.title(f"{self.TITLE} - Player {self._game_engine.game.current_player}")

    def _disable_input(self) -> None:
        super()._disable_input()
        self._root.title(self.TITLE)

    def _build_grid(self) -> None:
        total_buttons = BOARD_SIZE * BOARD_SIZE
        for i in range(total_buttons):
            btn = tk.Button(
                self._root,
                text="",
                width=7,
                height=3,
                font=("Helvetica", 32),
                command=partial(self._on_click, i),
            )
            row, col = divmod(i, BOARD_SIZE)
            btn.grid(row=row, column=col, padx=2, pady=2)
            self._buttons.append(btn)

    def _on_click(self, index: int) -> None:
        if not self._input_enabled or not self._running:
            return
        row, col = divmod(index, BOARD_SIZE)
        self._apply_move(row, col)

    def _render_board(self) -> None:
        for i, btn in enumerate(self._buttons):
            row, col = divmod(i, BOARD_SIZE)
            value = self._game_engine.game.board.board[row][col]
            btn.config(text=value if value is not None else "")

    def _show_end_message(self, msg: str) -> None:
        threading.Thread(target=self._show_end_message_internal, daemon=True, args=(msg,)).start()

    def _show_end_message_internal(self, msg: str) -> None:
        messagebox.showinfo("Game Over", msg)
        self._stop()

    def on_input_error(self, _exception: Exception) -> None:
        pass
