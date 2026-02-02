from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    player: str  # "X" or "O"
    row: int
    col: int


class TicTacToe:
    def __init__(self) -> None:
        self.board: list[list[str | None]] = [[None] * 3 for _ in range(3)]
        self.current_player = "X"
        self.winner: str | None = None

    def apply_move(self, move: Move) -> None:  # noqa: D102
        if self.winner:
            raise ValueError("Game over")

        if move.player != self.current_player:
            raise ValueError("Not your turn")

        if self.board[move.row][move.col] is not None:
            raise ValueError("Cell occupied")

        self.board[move.row][move.col] = move.player
        self._check_winner()
        self.current_player = "O" if self.current_player == "X" else "X"

    def _check_winner(self) -> None:
        lines: list[list[str | None] | tuple[str | None]] = []

        lines.extend(self.board)  # Horizontal lines
        lines.extend(zip(*self.board, strict=True))  # Vertical lines
        lines.append([self.board[i][i] for i in range(len(self.board))])  # First diagonal
        lines.append([self.board[i][len(self.board) - 1 - i] for i in range(len(self.board))])  # Second diagonal

        for line in lines:
            if line[0] and all(cell == line[0] for cell in line):
                self.winner = line[0]
