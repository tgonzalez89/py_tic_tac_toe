import random
from abc import ABC, abstractmethod

from py_tic_tac_toe.board import Move, PlayerSymbol
from py_tic_tac_toe.exception import LogicError
from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player


class AiPlayer(Player, ABC):
    def __init__(self, game: Game, symbol: PlayerSymbol) -> None:
        super().__init__(game, symbol)

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
        available_positions = self._game.board.get_available_positions()
        if not available_positions:
            return None
        return random.choice(available_positions)


class HardAiPlayer(AiPlayer):
    def _find_move(self) -> tuple[int, int] | None:  # noqa: C901, PLR0911, PLR0912
        """Strategy-based AI using human-like optimal heuristics."""
        available = self._game.board.get_available_positions()
        if not available:
            return None

        opponent: PlayerSymbol = "O" if self._symbol == "X" else "X"

        # 1) Win: If the player has two in a row, they can place a third to get three in a row.
        win_move = self._find_winning_move(self._symbol)
        if win_move:
            return win_move

        # 2) Block: If the opponent has two in a row, the player must play the third themselves to block the opponent.
        block_move = self._find_winning_move(opponent)
        if block_move:
            return block_move

        # 3) Fork: Cause a scenario where the player has two ways to win (two non-blocked lines of 2).
        fork_moves = self._find_fork_moves(self._symbol)
        if fork_moves:
            return fork_moves[0]

        # 4) Blocking an opponent's fork
        #    If there is only one possible fork for the opponent, the player should block it.
        #    Otherwise, the player should block all forks in any way
        #    that simultaneously allows them to make two in a row.
        #    Otherwise, the player should make a two in a row to force the opponent into defending,
        #    as long as it does not result in them producing a fork.
        #    For example, if "X" has two opposite corners and "O" has the center,
        #    "O" must not play a corner move to win.
        #    (Playing a corner move in this scenario produces a fork for "X" to win.)
        opponent_fork_moves = self._find_fork_moves(opponent)
        if opponent_fork_moves:
            if len(opponent_fork_moves) == 1:
                # Block the only fork
                return opponent_fork_moves[0]
            # Multiple forks possible, try to force opponent to defend
            # while not creating a fork for them
            force_move = self._find_forcing_move(opponent)
            if force_move:
                return force_move
            # If no safe forcing move, just block one of the forks
            return opponent_fork_moves[0]

        # 5) Center: A player marks the center.
        #    (If it is the first move of the game,
        #    playing a corner move gives the second player more opportunities to make a mistake and
        #    may therefore be the better choice; however, it makes no difference between perfect players.)
        if (1, 1) in available:
            return (1, 1)

        # 6) Opposite corner: If the opponent is in the corner, the player plays the opposite corner.
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        for corner in corners:
            r, c = corner
            if self._game.board.board[r][c] == opponent:
                opp_corner = abs(corner[0] - 2), abs(corner[1] - 2)
                if opp_corner in available:
                    return opp_corner

        # 7) Empty corner: The player plays in a corner square.
        for corner in corners:
            if corner in available:
                return corner

        # 8) Empty side: The player plays in a middle square on any of the four sides.
        sides = [(0, 1), (1, 0), (1, 2), (2, 1)]
        for side in sides:
            if side in available:
                return side

        # Fallback (should never reach here if board has available positions)
        return available[0] if available else None

    def _find_winning_move(self, symbol: PlayerSymbol) -> tuple[int, int] | None:
        """Find a move that wins the game for the given symbol."""
        for row, col in self._game.board.get_available_positions():
            # Simulate the move
            board_copy = self._game.board.clone()
            board_copy.apply_move(Move(symbol, row, col))

            # Check if this results in a win
            if board_copy.get_winner() == symbol:
                return (row, col)

        return None

    def _find_fork_moves(self, symbol: PlayerSymbol) -> list[tuple[int, int]]:
        """Find moves that create a fork (two ways to win) for the given symbol."""
        fork_moves = []

        for row, col in self._game.board.get_available_positions():
            # Simulate the move
            board_copy = self._game.board.clone()
            board_copy.apply_move(Move(symbol, row, col))

            # Count how many ways to win after this move
            winning_moves = 0
            for next_row, next_col in board_copy.get_available_positions():
                board_copy2 = board_copy.clone()
                board_copy2.apply_move(Move(symbol, next_row, next_col))
                if board_copy2.get_winner() == symbol:
                    winning_moves += 1

            # A fork means at least 2 ways to win
            if winning_moves >= 2:  # noqa: PLR2004
                fork_moves.append((row, col))

        return fork_moves

    def _find_forcing_move(self, opponent_symbol: PlayerSymbol) -> tuple[int, int] | None:
        """Find a move that creates a threat, forcing opponent to defend without creating a fork for them."""
        for row, col in self._game.board.get_available_positions():
            # Simulate the move
            board_copy = self._game.board.clone()
            board_copy.apply_move(Move(self._symbol, row, col))

            # Check if this creates exactly one winning threat (opponent must block)
            winning_moves = []
            for next_row, next_col in board_copy.get_available_positions():
                board_copy2 = board_copy.clone()
                board_copy2.apply_move(Move(self._symbol, next_row, next_col))
                if board_copy2.get_winner() == self._symbol:
                    winning_moves.append((next_row, next_col))

            # If we have exactly one winning move (a threat), check if blocking it doesn't create a fork for opponent
            if len(winning_moves) == 1:
                block_row, block_col = winning_moves[0]
                # Simulate opponent blocking
                board_with_block = board_copy.clone()
                board_with_block.apply_move(Move(opponent_symbol, block_row, block_col))

                # Check if opponent now has a fork
                opponent_winning_count = 0
                for opp_row, opp_col in board_with_block.get_available_positions():
                    board_copy3 = board_with_block.clone()
                    board_copy3.apply_move(Move(opponent_symbol, opp_row, opp_col))

                    # Count opponent's winning moves
                    opp_winning_moves = 0
                    for final_row, final_col in board_copy3.get_available_positions():
                        board_copy4 = board_copy3.clone()
                        board_copy4.apply_move(Move(opponent_symbol, final_row, final_col))
                        if board_copy4.get_winner() == opponent_symbol:
                            opp_winning_moves += 1

                    if opp_winning_moves >= 2:  # noqa: PLR2004
                        opponent_winning_count += 1
                        break

                # If opponent doesn't get a fork after blocking, this is a good forcing move
                if opponent_winning_count == 0:
                    return (row, col)

        return None
