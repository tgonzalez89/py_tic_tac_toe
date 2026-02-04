from typing import Any

from py_tic_tac_toe.event_bus.event_bus import EnableInput, EventBus, MoveRequested, StartTurn, StateUpdated
from py_tic_tac_toe.network.tcp_transport import TcpTransport
from py_tic_tac_toe.player.player import Player


class RemoteNetworkPlayer(Player):
    """Host-side player: receives moves from network, forwards engine state to client."""

    def __init__(self, event_bus: EventBus, symbol: str, transport: TcpTransport) -> None:
        super().__init__(event_bus, symbol)
        self.transport = transport
        self.transport.send({"type": "AssignRole", "role": self.symbol})
        msg = self.transport.recv()
        if msg.get("type") != "AssignRoleAck":
            err_msg = "Error assigning role."
            raise RuntimeError(err_msg)

        self.start_turn_event_cache: StartTurn

        self.event_bus.subscribe(StateUpdated, self._on_state_updated)

        self.transport.add_recv_handler("MoveRequested", self._on_network_message)

    def _on_start_turn(self, event: StartTurn) -> None:
        if event.current_player != self.symbol:
            return

        self.start_turn_event_cache = event
        self.transport.send({"type": "StartTurn", "board": event.board, "current_player": event.current_player})

    def _on_state_updated(self, event: StateUpdated) -> None:
        self.transport.send(
            {
                "type": "StateUpdated",
                "board": event.board,
                "current_player": event.current_player,
                "winner": event.winner,
            },
        )

    def _on_network_message(self, msg: dict[str, Any]) -> None:
        if msg["type"] == "MoveRequested":
            try:
                self.event_bus.publish(MoveRequested(msg["player"], msg["row"], msg["col"]))
            except ValueError:
                self.event_bus.publish(self.start_turn_event_cache)


class LocalNetworkPlayer(Player):
    """Client-side player: sends local moves to host, republishes state locally."""

    def __init__(self, event_bus: EventBus, transport: TcpTransport) -> None:
        self.transport = transport
        msg = self.transport.recv()
        if msg.get("type") == "AssignRole" and isinstance(msg.get("role"), str):
            super().__init__(event_bus, str(msg["role"]))
        else:
            err_msg = "Error assigning role."
            raise RuntimeError(err_msg)
        self.transport.send({"type": "AssignRoleAck"})

        self.event_bus.subscribe(MoveRequested, self._on_move_requested)

        self.transport.add_recv_handler("StartTurn", self._on_network_message)
        self.transport.add_recv_handler("StateUpdated", self._on_network_message)

    def _on_start_turn(self, event: StartTurn) -> None:
        if self.symbol != event.current_player:
            return

        self.event_bus.publish(EnableInput(self.symbol))

    def _on_move_requested(self, event: MoveRequested) -> None:
        if event.player != self.symbol:
            return

        self.transport.send({"type": "MoveRequested", "player": event.player, "row": event.row, "col": event.col})

    def _on_network_message(self, msg: dict[str, Any]) -> None:
        match msg["type"]:
            case "StartTurn":
                self.event_bus.publish(StartTurn(msg["board"], msg["current_player"]))
            case "StateUpdated":
                self.event_bus.publish(StateUpdated(msg["board"], msg["current_player"], msg["winner"]))

    def _on_assign_role(self, msg: dict[str, Any]) -> None:
        if msg["type"] == "AssignRole":
            self.symbol = msg["role"]
