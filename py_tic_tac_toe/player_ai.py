import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import deepcopy

from py_tic_tac_toe.board import Board, Move, PlayerSymbol
from py_tic_tac_toe.exception import LogicError
from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player


class AiPlayer(Player, ABC):
    def __init__(self, symbol: PlayerSymbol, game: Game) -> None:
        super().__init__(symbol, game)
        self._apply_move_cb: Callable[[int, int], bool]

    def set_apply_move_cb(self, callback: Callable[[int, int], bool]) -> None:
        self._apply_move_cb = callback

    def start_turn(self) -> None:
        move = self._find_move()
        if move is None:
            msg = f"No moves available for player {self._symbol}, but game not over."
            raise LogicError(msg)
        row, col = move
        self._apply_move_cb(row, col)

    def apply_move(self, row: int, col: int) -> bool:
        self._game.apply_move(Move(self._symbol, row, col))
        return True

    @abstractmethod
    def _find_move(self) -> tuple[int, int] | None:
        pass


class RandomAiPlayer(AiPlayer):
    def _find_move(self) -> tuple[int, int] | None:
        available_positions = self._game.board.get_available_positions()
        if not available_positions:
            return None
        return random.choice(available_positions)


class HardAiPlayer(AiPlayer):
    def _find_move(self) -> tuple[int, int] | None:
        best_score = -1000000
        best_move: tuple[int, int] | None = None
        board: Board = deepcopy(self._game.board)
        for row, col in self._game.board.get_available_positions():
            board.board[row][col] = self._symbol
            score = self._minimax(board, self._opponent(self._symbol), 1)
            board.board[row][col] = None
            if score > best_score:
                best_score = score
                best_move = (row, col)
        return best_move

    def _minimax(self, board: Board, player: PlayerSymbol, depth: int) -> int:
        winner = board.get_winner()
        if winner == self._symbol:
            return 10 - depth
        if winner == self._opponent(self._symbol):
            return depth - 10
        if board.is_draw():
            return 0
        is_maximizing = player == self._symbol
        best_score = -100 if is_maximizing else 100
        for row, col in board.get_available_positions():
            board.board[row][col] = player
            score = self._minimax(board, self._opponent(player), depth + 1)
            board.board[row][col] = None
            best_score = max(best_score, score) if is_maximizing else min(best_score, score)
        return best_score

    def _opponent(self, player: PlayerSymbol) -> PlayerSymbol:
        return "O" if player == "X" else "X"
