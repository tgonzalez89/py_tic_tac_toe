import sys
import threading
import tkinter as tk
from functools import partial
from tkinter import messagebox

from py_tic_tac_toe.event_bus.event_bus import EnableInput, EventBus, InvalidMove, MoveRequested, StateUpdated
from py_tic_tac_toe.game.board_utils import BOARD_SIZE, PlayerSymbol, get_winner, is_board_full
from py_tic_tac_toe.ui.ui import Ui


class TkUi(Ui):
    def __init__(self, event_bus: EventBus) -> None:
        super().__init__(event_bus)

        self._current_player: PlayerSymbol
        self._game_running = False
        self._buttons: list[tk.Button] = []
        self._input_enabled = False

    def start(self) -> None:  # noqa: D102
        self._root = tk.Tk()
        self._root.title("Tic-Tac-Toe (Tk)")

        self._build_grid()

        self._game_running = True

        self._root.after(0, self._root.deiconify)
        self._started = True
        self._root.mainloop()
        sys.exit()

    def _enable_input(self, event: EnableInput) -> None:
        self._current_player = event.player
        self._input_enabled = True
        self._root.title(f"Tic-Tac-Toe (Tk) - Player {event.player}")

    def _disable_input(self) -> None:
        self._input_enabled = False
        self._root.title("Tic-Tac-Toe (Tk)")

    # -----------------------------
    # UI construction
    # -----------------------------

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

    # -----------------------------
    # Event handling
    # -----------------------------

    def _on_click(self, index: int) -> None:
        if not self._input_enabled or not self._game_running:
            return

        row, col = divmod(index, BOARD_SIZE)

        self._disable_input()
        self._event_bus.publish(MoveRequested(self._current_player, row, col))

    def _on_state_updated(self, event: StateUpdated) -> None:
        self._current_player = event.player

        for i, btn in enumerate(self._buttons):
            row, col = divmod(i, BOARD_SIZE)
            value = event.board[row][col]
            btn.config(text=value if value is not None else "")

        winner = get_winner(event.board)
        if winner:
            self._show_end_message(f"Winner: {winner}")
        elif is_board_full(event.board):
            self._show_end_message("It's a draw")

    def _show_end_message(self, msg: str) -> None:
        self._game_running = False
        threading.Thread(target=self._show_end_message_internal, daemon=True, args=(msg,)).start()

    def _show_end_message_internal(self, msg: str) -> None:
        messagebox.showinfo("Game Over", msg)
        # Schedule destroy on the main Tk thread to avoid thread conflicts
        self._root.after(0, self._root.quit)

    def _on_invalid_move(self, event: InvalidMove) -> None:
        self._enable_input(EnableInput(event.player))
