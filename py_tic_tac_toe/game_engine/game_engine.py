from py_tic_tac_toe.event_bus.event_bus import (
    BoardProvided,
    BoardRequested,
    EventBus,
    InvalidMove,
    MoveRequested,
    StartTurn,
    StateUpdated,
)
from py_tic_tac_toe.game.game import Move, TicTacToe
from py_tic_tac_toe.util.errors import InvalidMoveError, LogicError


class GameEngine:
    def __init__(self, event_bus: EventBus) -> None:
        self._game = TicTacToe()
        self._event_bus = event_bus
        self._event_bus.subscribe(MoveRequested, self._on_move_requested)
        self._event_bus.subscribe(BoardRequested, self._on_board_requested)

    def start(self) -> None:  # noqa: D102
        self._request_state_updated()
        self._request_start_turn()

    def _on_move_requested(self, event: MoveRequested) -> None:
        try:
            self._game.apply_move(Move(event.player, event.row, event.col))
        except InvalidMoveError as e:
            self._event_bus.publish(InvalidMove(str(e), event.player, event.row, event.col))
            return
        except IndexError as e:
            # Serious logic error, let it propagate.
            # TODO: think if this should be handled better (request move again, show something in the UI, etc.)
            raise LogicError("Move out of bounds") from e

        self._request_state_updated()

        if not self._game.winner:
            self._request_start_turn()

    def _request_state_updated(self) -> None:
        self._event_bus.publish(StateUpdated(self._game.board, self._game.current_player, self._game.winner))

    def _request_start_turn(self) -> None:
        self._event_bus.publish(StartTurn(self._game.current_player))

    def _on_board_requested(self, event: BoardRequested) -> None:
        self._event_bus.publish(BoardProvided(event.player, self._game.board))
