import os
import tkinter as tk
from functools import partial
from tkinter import messagebox

from py_tic_tac_toe.engine.game_engine import GameEngine, MoveRequested, StateUpdated


class TkUI:
    def __init__(self, game_engine: GameEngine) -> None:
        self.game_engine = game_engine
        self.root = tk.Tk()
        self.root.title("Tic-Tac-Toe (Tk)")

        self.buttons: list[tk.Button] = []
        self.current_player = "X"
        self.game_over = False

        self._build_grid()

        self.game_engine.subscribe(StateUpdated, self._on_state_updated)

    def start(self) -> None:  # noqa: D102
        self.root.after(0, self.root.deiconify)
        self.root.mainloop()
        os._exit(0)

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
        if self.game_over or self.current_player is None:
            return

        row, col = divmod(index, 3)

        self.game_engine.on_move_requested(
            MoveRequested(
                player=self.current_player,
                row=row,
                col=col,
            ),
        )

    def _on_state_updated(self, event: StateUpdated) -> None:
        self.current_player = event.current_player
        self.game_over = event.winner is not None

        for i, btn in enumerate(self.buttons):
            row, col = divmod(i, 3)
            value = event.board[row][col]
            btn.config(text=value if value is not None else "")

        if event.winner:
            messagebox.showinfo("Game Over", f"Winner: {event.winner}")
            self.game_over = True
            os._exit(0)
        elif all(all(cell is not None for cell in row) for row in event.board):
            messagebox.showinfo("Game Over", "It's a draw")
            self.game_over = True
            os._exit(0)
        else:
            self.root.title(f"Tic-Tac-Toe (Tk) - Player {self.current_player}")
