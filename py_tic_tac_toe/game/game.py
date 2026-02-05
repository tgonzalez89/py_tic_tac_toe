from dataclasses import dataclass

from py_tic_tac_toe.game.board_utils import BOARD_SIZE, PlayerSymbol, get_winner
from py_tic_tac_toe.util.errors import InvalidMoveError


@dataclass(frozen=True)
class Move:
    player: PlayerSymbol
    row: int
    col: int


class TicTacToe:
    def __init__(self) -> None:
        self._board: list[list[PlayerSymbol | None]] = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self._current_player: PlayerSymbol = "X"

    @property
    def board(self) -> list[list[PlayerSymbol | None]]:  # noqa: D102
        return self._board

    @property
    def current_player(self) -> PlayerSymbol:  # noqa: D102
        return self._current_player

    def apply_move(self, move: Move) -> None:  # noqa: D102
        if not (0 <= move.row < BOARD_SIZE) or not (0 <= move.col < BOARD_SIZE):
            raise IndexError("Move out of bounds")

        if self._board[move.row][move.col] is not None:
            raise InvalidMoveError("Cell occupied")

        if move.player != self._current_player:
            raise InvalidMoveError("Not your turn")

        if get_winner(self._board):
            raise InvalidMoveError("Game over")

        self._board[move.row][move.col] = move.player
        self._current_player = "O" if self._current_player == "X" else "X"
