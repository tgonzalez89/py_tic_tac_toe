from typing import Final, Literal

BOARD_SIZE: Final = 3

type PlayerSymbol = Literal["X", "O"]


def is_board_full(board: list[list[PlayerSymbol | None]]) -> bool:  # noqa: D103
    return all(all(cell is not None for cell in row) for row in board)


def get_available_moves(board: list[list[PlayerSymbol | None]]) -> list[tuple[int, int]]:  # noqa: D103
    return [(r, c) for r in range(len(board)) for c in range(len(board[0])) if board[r][c] is None]


def get_winner(board: list[list[PlayerSymbol | None]]) -> str | None:  # noqa: D103
    lines: list[list[PlayerSymbol | None]] = []

    lines.extend(board)  # Horizontal lines
    lines.extend([list(row) for row in zip(*board, strict=True)])  # Vertical lines
    lines.append([board[i][i] for i in range(len(board))])  # First diagonal
    lines.append([board[i][len(board) - 1 - i] for i in range(len(board))])  # Second diagonal

    for line in lines:
        if line[0] and all(cell == line[0] for cell in line):
            return line[0]
    return None


def is_draw(board: list[list[PlayerSymbol | None]]) -> bool:  # noqa: D103
    return is_board_full(board) and get_winner(board) is None
