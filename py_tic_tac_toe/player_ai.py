import random
from abc import ABC, abstractmethod

from py_tic_tac_toe.board import Board, PlayerSymbol
from py_tic_tac_toe.exception import LogicError
from py_tic_tac_toe.player import Player


class AiPlayer(Player, ABC):
    def __init__(self, symbol: PlayerSymbol, board: Board) -> None:
        super().__init__(symbol)
        self._board = board

    def start_turn(self) -> None:
        move = self._find_move()
        if move is None:
            msg = f"No moves available for player {self._symbol}, but game not over."
            raise LogicError(msg)
        row, col = move
        self.queue_move(row, col)

    @abstractmethod
    def _find_move(self) -> tuple[int, int] | None:
        pass


class RandomAiPlayer(AiPlayer):
    def _find_move(self) -> tuple[int, int] | None:
        available_positions = self._board.get_available_positions()
        if not available_positions:
            return None
        return random.choice(available_positions)


class HardAiPlayer(AiPlayer):
    def _find_move(self) -> tuple[int, int] | None:
        """Strategy-based AI using human-like optimal heuristics."""
        available = self._board.get_available_positions()
        if not available:
            return None

        opponent: PlayerSymbol = "O" if self._symbol == "X" else "X"

        # 1. Win if possible (finish our line)
        for row, col in available:
            self._board.board[row][col] = self._symbol
            if self._board.get_winner() == self._symbol:
                self._board.board[row][col] = None
                return (row, col)
            self._board.board[row][col] = None

        # 2. Block opponent's winning move
        for row, col in available:
            self._board.board[row][col] = opponent
            if self._board.get_winner() == opponent:
                self._board.board[row][col] = None
                return (row, col)
            self._board.board[row][col] = None

        # 3. Take center (strongest position)
        if (1, 1) in available:
            return (1, 1)

        # 4. Take corner (next best positions)
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        corner_moves = [c for c in corners if c in available]
        if corner_moves:
            return random.choice(corner_moves)

        # 5. Take edge (remaining positions)
        return available[0]
