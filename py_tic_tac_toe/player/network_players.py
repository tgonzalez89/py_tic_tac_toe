from typing import Any, cast

from py_tic_tac_toe.event_bus.event_bus import (
    EnableInput,
    EventBus,
    InvalidMove,
    MoveRequested,
    StartTurn,
    StateUpdated,
)
from py_tic_tac_toe.game.board_utils import PlayerSymbol
from py_tic_tac_toe.network.tcp_transport import TcpTransport
from py_tic_tac_toe.player.player import Player
from py_tic_tac_toe.util.errors import LogicError


class NetworkPlayer(Player):
    def __init__(self, event_bus: EventBus, symbol: PlayerSymbol, transport: TcpTransport) -> None:
        super().__init__(event_bus, symbol)
        self._transport = transport


class RemoteNetworkPlayer(NetworkPlayer):
    """Host-side player: receives moves from network, forwards engine state to client."""

    def __init__(self, event_bus: EventBus, symbol: PlayerSymbol, transport: TcpTransport) -> None:
        super().__init__(event_bus, symbol, transport)

        self._transport.send({"type": "AssignRole", "role": self._symbol})

        msg = self._transport.recv()
        if msg is None or msg.get("type") != "AssignRoleAck":
            raise LogicError("Ack for assign role msg not received")

        self._event_bus.subscribe(StateUpdated, self._on_state_updated)
        self._event_bus.subscribe(InvalidMove, self._on_invalid_move)

        self._transport.add_recv_handler("MoveRequested", self._on_network_message)

    def _on_start_turn(self, event: StartTurn) -> None:
        if event.player != self._symbol:
            return

        self._transport.send(event.to_dict())

    def _on_state_updated(self, event: StateUpdated) -> None:
        self._transport.send(event.to_dict())

    def _on_network_message(self, msg: dict[str, Any]) -> None:
        if msg.get("type") == "MoveRequested":
            self._event_bus.publish(MoveRequested.to_instance(msg))

    def _on_invalid_move(self, event: InvalidMove) -> None:
        if event.player != self._symbol:
            return

        # Re-trigger start turn to request move again from remote player
        self._event_bus.publish(StartTurn(event.player))


class LocalNetworkPlayer(NetworkPlayer):
    """Client-side player: sends local moves to host, republishes state locally."""

    def __init__(self, event_bus: EventBus, transport: TcpTransport) -> None:
        msg = transport.recv()
        if msg is None or msg.get("type") != "AssignRole" or not isinstance(msg.get("role"), str):
            raise LogicError("Assign role msg not received")

        super().__init__(event_bus, cast("PlayerSymbol", msg["role"]), transport)

        self._transport.send({"type": "AssignRoleAck"})

        self._event_bus.subscribe(MoveRequested, self._on_move_requested)

        self._transport.add_recv_handler("StartTurn", self._on_network_message)
        self._transport.add_recv_handler("StateUpdated", self._on_network_message)

    def _on_start_turn(self, event: StartTurn) -> None:
        if self._symbol != event.player:
            return

        self._event_bus.publish(EnableInput(self._symbol))

    def _on_move_requested(self, event: MoveRequested) -> None:
        if event.player != self._symbol:
            return

        self._transport.send(event.to_dict())

    def _on_network_message(self, msg: dict[str, Any]) -> None:
        match msg.get("type"):
            case "StartTurn":
                self._event_bus.publish(StartTurn.to_instance(msg))
            case "StateUpdated":
                self._event_bus.publish(StateUpdated.to_instance(msg))
