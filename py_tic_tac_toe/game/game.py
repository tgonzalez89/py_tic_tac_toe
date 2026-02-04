from dataclasses import dataclass

from py_tic_tac_toe.util.errors import InvalidMoveError


@dataclass(frozen=True)
class Move:
    player: str  # "X" or "O"
    row: int
    col: int


class TicTacToe:
    def __init__(self) -> None:
        self._board: list[list[str | None]] = [[None] * 3 for _ in range(3)]
        self._current_player = "X"
        self._winner: str | None = None

    @property
    def board(self) -> list[list[str | None]]:  # noqa: D102
        return self._board

    @property
    def current_player(self) -> str:  # noqa: D102
        return self._current_player

    @property
    def winner(self) -> str | None:  # noqa: D102
        return self._winner

    def apply_move(self, move: Move) -> None:  # noqa: D102
        if self._winner:
            raise InvalidMoveError("Game over")

        if move.player != self._current_player:
            raise InvalidMoveError("Not your turn")

        if self._board[move.row][move.col] is not None:
            raise InvalidMoveError("Cell occupied")

        self._board[move.row][move.col] = move.player
        self._check_winner()
        self._current_player = "O" if self._current_player == "X" else "X"

    def _check_winner(self) -> None:
        lines: list[list[str | None]] = []

        lines.extend(self._board)  # Horizontal lines
        lines.extend([list(row) for row in zip(*self.board, strict=True)])  # Vertical lines
        lines.append([self._board[i][i] for i in range(len(self._board))])  # First diagonal
        lines.append([self._board[i][len(self._board) - 1 - i] for i in range(len(self._board))])  # Second diagonal

        for line in lines:
            if line[0] and all(cell == line[0] for cell in line):
                self._winner = line[0]
