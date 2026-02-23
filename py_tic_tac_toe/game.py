from py_tic_tac_toe.board import Board, Move, PlayerSymbol
from py_tic_tac_toe.exception import InvalidMoveError


class Game:
    def __init__(self) -> None:
        self._board = Board()
        self._current_player_symbol: PlayerSymbol = "X"

    @property
    def board(self) -> Board:
        return self._board

    @property
    def current_player_symbol(self) -> PlayerSymbol:
        return self._current_player_symbol

    def validate_and_apply_move(self, move: Move) -> None:
        self.validate_move(move)
        self.apply_move(move)

    def validate_move(self, move: Move) -> None:
        if move.player != self._current_player_symbol:
            raise InvalidMoveError("Not your turn.")
        self._board.validate_move(move)

    def apply_move(self, move: Move) -> None:
        self._board.apply_move(move)
        self._current_player_symbol = "O" if self._current_player_symbol == "X" else "X"
