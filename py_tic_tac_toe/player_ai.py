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
        best_score = -1000000
        best_move: tuple[int, int] | None = None
        opponent: PlayerSymbol = "O" if self._symbol == "X" else "X"
        board = self._board.clone()
        for row, col in self._board.get_available_positions():
            board.board[row][col] = self._symbol
            # Alpha-beta pruning: alpha=-inf, beta=+inf for root call
            score = self._minimax_ab(board, opponent, 1, -1000000, 1000000)
            board.board[row][col] = None
            if score > best_score:
                best_score = score
                best_move = (row, col)
        return best_move

    def _minimax_ab(
        self,
        board: Board,
        player: PlayerSymbol,
        depth: int,
        alpha: int,
        beta: int,
    ) -> int:
        """Minimax with alpha-beta pruning for faster evaluation."""
        winner = board.get_winner()
        if winner == self._symbol:
            return 10 - depth
        if winner != player and winner is not None:  # opponent won
            return depth - 10
        if board.is_draw():
            return 0

        opponent: PlayerSymbol = "O" if player == "X" else "X"
        if player == self._symbol:  # maximizing player
            for row, col in board.get_available_positions():
                board.board[row][col] = player
                score = self._minimax_ab(board, opponent, depth + 1, alpha, beta)
                board.board[row][col] = None
                alpha = max(alpha, score)
                if beta <= alpha:
                    break  # Beta cutoff - prune remaining branches
            return alpha
        # minimizing player
        for row, col in board.get_available_positions():
            board.board[row][col] = player
            score = self._minimax_ab(board, opponent, depth + 1, alpha, beta)
            board.board[row][col] = None
            beta = min(beta, score)
            if beta <= alpha:
                break  # Alpha cutoff - prune remaining branches
        return beta
