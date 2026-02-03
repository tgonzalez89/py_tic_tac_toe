from py_tic_tac_toe.game.game import Move, TicTacToe
from py_tic_tac_toe.game_engine.event import EventBus, MoveRequested, StartTurn, StateUpdated


class GameEngine:
    def __init__(self, event_bus: EventBus) -> None:
        self.game = TicTacToe()
        self.event_bus = event_bus
        self.event_bus.subscribe(MoveRequested, self._on_move_requested)

    def start(self) -> None:  # noqa: D102
        self._request_state_updated()
        self._request_start_turn()

    def _on_move_requested(self, event: MoveRequested) -> None:
        self.game.apply_move(Move(event.player, event.row, event.col))

        self._request_state_updated()

        if not self.game.winner:
            self._request_start_turn()

    def _request_state_updated(self) -> None:
        self.event_bus.publish(StateUpdated(self.game.board, self.game.current_player, self.game.winner))

    def _request_start_turn(self) -> None:
        self.event_bus.publish(StartTurn(self.game.board, self.game.current_player))
