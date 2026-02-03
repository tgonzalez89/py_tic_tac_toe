import os
import threading
import tkinter as tk
from functools import partial
from tkinter import messagebox

from py_tic_tac_toe.game_engine.event import EnableInput, EventBus, InvalidMove, MoveRequested, StateUpdated
from py_tic_tac_toe.ui.ui import Ui


class TkUi(Ui):
    def __init__(self, event_bus: EventBus) -> None:
        super().__init__(event_bus)

        self.current_player: str
        self.game_running = False
        self.buttons: list[tk.Button] = []
        self.input_enabled = False

    def start(self) -> None:  # noqa: D102
        self.root = tk.Tk()
        self.root.title("Tic-Tac-Toe (Tk)")

        self._build_grid()

        self.game_running = True

        self.root.after(0, self.root.deiconify)
        self._started = True
        self.root.mainloop()
        os._exit(0)

    def _enable_input(self, event: EnableInput) -> None:
        self.current_player = event.player
        self.input_enabled = True
        self.root.title(f"Tic-Tac-Toe (Tk) - Player {event.player}")

    def _disable_input(self) -> None:
        self.input_enabled = False
        self.root.title("Tic-Tac-Toe (Tk)")

    # -----------------------------
    # UI construction
    # -----------------------------

    def _build_grid(self) -> None:
        for i in range(9):
            btn = tk.Button(
                self.root,
                text="",
                width=7,
                height=3,
                font=("Helvetica", 32),
                command=partial(self._on_click, i),
            )
            btn.grid(row=i // 3, column=i % 3, padx=2, pady=2)
            self.buttons.append(btn)

    # -----------------------------
    # Event handling
    # -----------------------------

    def _on_click(self, index: int) -> None:
        if not self.input_enabled or not self.game_running:
            return

        row, col = divmod(index, 3)

        self._disable_input()

        try:
            self.event_bus.publish(MoveRequested(self.current_player, row, col))
        except ValueError:
            self._enable_input(EnableInput(self.current_player))

    def _on_state_updated(self, event: StateUpdated) -> None:
        self.current_player = event.current_player

        for i, btn in enumerate(self.buttons):
            row, col = divmod(i, 3)
            value = event.board[row][col]
            btn.config(text=value if value is not None else "")

        if event.winner:
            self._show_end_message(f"Winner: {event.winner}")
        elif all(all(cell is not None for cell in row) for row in event.board):
            self._show_end_message("It's a draw")

    def _show_end_message(self, msg: str) -> None:
        self.game_running = False
        threading.Thread(target=self._show_end_message_internal, daemon=True, args=(msg,)).start()

    def _show_end_message_internal(self, msg: str) -> None:
        messagebox.showinfo("Game Over", msg)
        self.root.destroy()

    def _on_error(self, event: InvalidMove) -> None:
        pass
