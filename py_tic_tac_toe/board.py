from dataclasses import dataclass
from typing import Final, Literal

from py_tic_tac_toe.exception import InvalidMoveError

BOARD_SIZE: Final = 3
type PlayerSymbol = Literal["X", "O"]


@dataclass(frozen=True, slots=True)
class Move:
    player: PlayerSymbol
    row: int
    col: int


class Board:
    def __init__(self) -> None:
        self._board: list[list[PlayerSymbol | None]] = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]

    @property
    def board(self) -> list[list[PlayerSymbol | None]]:
        return self._board

    def clone(self) -> "Board":
        copied = Board()
        copied._board = [row[:] for row in self._board]
        return copied

    def apply_move(self, move: Move) -> None:
        if not (0 <= move.row < len(self._board)) or not (0 <= move.col < len(self._board[0])):
            raise IndexError("Move out of bounds.")

        if self._board[move.row][move.col] is not None:
            raise InvalidMoveError("Cell occupied.")

        if self.get_winner():
            raise InvalidMoveError("Game over.")

        self._board[move.row][move.col] = move.player

    def get_available_positions(self) -> list[tuple[int, int]]:
        return [
            (r, c) for r in range(len(self._board)) for c in range(len(self._board[0])) if self._board[r][c] is None
        ]

    def is_full(self) -> bool:
        return all(all(cell is not None for cell in row) for row in self._board)

    def get_winner(self) -> str | None:
        lines: list[list[PlayerSymbol | None]] = []

        lines.extend(self._board)  # Horizontal lines
        lines.extend([list(row) for row in zip(*self._board, strict=True)])  # Vertical lines
        lines.append([self._board[i][i] for i in range(len(self._board))])  # First diagonal
        lines.append([self._board[i][len(self._board) - 1 - i] for i in range(len(self._board))])  # Second diagonal

        for line in lines:
            if line[0] is not None and all(cell == line[0] for cell in line[1:]):
                return line[0]
        return None

    def is_draw(self) -> bool:
        return self.is_full() and self.get_winner() is None
