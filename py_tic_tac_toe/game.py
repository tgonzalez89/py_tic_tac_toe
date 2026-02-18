from py_tic_tac_toe.board import Board, Move, PlayerSymbol
from py_tic_tac_toe.exception import InvalidMoveError


class Game:
    def __init__(self) -> None:
        self._board = Board()
        self._current_player: PlayerSymbol = "X"

    @property
    def board(self) -> Board:
        return self._board

    @property
    def current_player(self) -> PlayerSymbol:
        return self._current_player

    def apply_move(self, move: Move) -> None:
        if move.player != self._current_player:
            raise InvalidMoveError("Not your turn")
        self._board.apply_move(move)
        self._current_player = "O" if self._current_player == "X" else "X"
