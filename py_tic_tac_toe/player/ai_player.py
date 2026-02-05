import random
from abc import ABC, abstractmethod
from copy import deepcopy

from py_tic_tac_toe.event_bus.event_bus import (
    AiThinkingComplete,
    BoardProvided,
    BoardRequested,
    EventBus,
    MoveRequested,
    StartTurn,
)
from py_tic_tac_toe.game.board_utils import PlayerSymbol, get_available_moves, get_winner, is_draw
from py_tic_tac_toe.player.player import Player
from py_tic_tac_toe.util.errors import LogicError


class AiPlayer(Player, ABC):
    def __init__(self, event_bus: EventBus, symbol: PlayerSymbol) -> None:
        super().__init__(event_bus, symbol)
        self._event_bus.subscribe(BoardProvided, self._on_board_provided)
        self._event_bus.subscribe(AiThinkingComplete, self._on_thinking_complete)

    def _on_start_turn(self, event: StartTurn) -> None:
        if self._symbol != event.player:
            return

        # Request board to make move decision
        self._event_bus.publish(BoardRequested(self._symbol))

    def _on_board_provided(self, event: BoardProvided) -> None:
        if self._symbol != event.player:
            return

        # Queue AI thinking asynchronously to avoid blocking on deep computation
        move = self._find_move(event.board)
        if move is None:
            msg = f"No moves available for player {self._symbol}, but game not over"
            raise LogicError(msg)
        row, col = move

        self._event_bus.publish_async(AiThinkingComplete(self._symbol, row, col))

    def _on_thinking_complete(self, event: AiThinkingComplete) -> None:
        if self._symbol != event.player:
            return

        self._event_bus.publish(MoveRequested(self._symbol, event.row, event.col))

    @abstractmethod
    def _find_move(self, board: list[list[PlayerSymbol | None]]) -> tuple[int, int] | None:
        pass


class RandomAiPlayer(AiPlayer):
    def _find_move(self, board: list[list[PlayerSymbol | None]]) -> tuple[int, int] | None:
        choices = get_available_moves(board)
        if not choices:
            return None
        return random.choice(choices)


class HardAiPlayer(AiPlayer):
    def _find_move(self, board: list[list[PlayerSymbol | None]]) -> tuple[int, int] | None:
        best_score = -1000000
        best_move: tuple[int, int] | None = None
        board = deepcopy(board)

        for row, col in get_available_moves(board):
            board[row][col] = self._symbol
            score = self._minimax(board, self._opponent(self._symbol), 1)
            board[row][col] = None

            if score > best_score:
                best_score = score
                best_move = (row, col)

        return best_move

    def _minimax(self, board: list[list[PlayerSymbol | None]], player: PlayerSymbol, depth: int) -> int:
        winner = get_winner(board)
        if winner == self._symbol:
            return 10 - depth
        if winner == self._opponent(self._symbol):
            return depth - 10
        if is_draw(board):
            return 0

        is_maximizing = player == self._symbol
        best_score = -100 if is_maximizing else 100

        for row, col in get_available_moves(board):
            board[row][col] = player
            score = self._minimax(board, self._opponent(player), depth + 1)
            board[row][col] = None

            best_score = max(best_score, score) if is_maximizing else min(best_score, score)

        return best_score

    def _opponent(self, player: PlayerSymbol) -> PlayerSymbol:
        return "O" if player == "X" else "X"
