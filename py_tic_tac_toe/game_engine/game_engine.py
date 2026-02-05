from py_tic_tac_toe.event_bus.event_bus import (
    BoardProvided,
    BoardRequested,
    EventBus,
    InvalidMove,
    MoveRequested,
    StartTurn,
    StateUpdated,
)
from py_tic_tac_toe.game.board_utils import get_winner, is_board_full
from py_tic_tac_toe.game.game import Move, TicTacToe
from py_tic_tac_toe.util.errors import InvalidMoveError, LogicError


class GameEngine:
    def __init__(self, event_bus: EventBus) -> None:
        self._game = TicTacToe()
        self._event_bus = event_bus
        self._event_bus.subscribe(MoveRequested, self._on_move_requested)
        self._event_bus.subscribe(BoardRequested, self._on_board_requested)

    def start(self) -> None:  # noqa: D102
        self._publish_state_updated()
        self._publish_start_turn()

    def _on_move_requested(self, event: MoveRequested) -> None:
        try:
            self._game.apply_move(Move(event.player, event.row, event.col))
        except InvalidMoveError as e:
            self._event_bus.publish(InvalidMove(event.player, event.row, event.col, str(e)))
            self._publish_start_turn()  # Invalid move: request move again without switching player
            return
        except IndexError as e:
            # Serious logic error, let it propagate.
            # TODO: think if this should be handled better (request move again, show something in the UI, etc.)
            raise LogicError from e

        self._publish_state_updated()  # State updated after successful move
        self._publish_start_turn()  # Start next turn: active player will do it's job

    def _publish_state_updated(self) -> None:
        self._event_bus.publish(StateUpdated(self._game.current_player, self._game.board))

    def _publish_start_turn(self) -> None:
        if not get_winner(self._game.board) and not is_board_full(self._game.board):
            self._event_bus.publish(StartTurn(self._game.current_player))

    def _on_board_requested(self, event: BoardRequested) -> None:
        self._event_bus.publish(BoardProvided(event.player, self._game.board))
