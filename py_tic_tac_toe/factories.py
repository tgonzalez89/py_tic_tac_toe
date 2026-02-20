"""Factory functions for creating game components.

Provides factories for creating:
- Players (local human, AI, network)
- Game engines
- UIs (terminal, pygame, tk)
- Complete game setups
"""

from typing import Literal

from py_tic_tac_toe.board import PlayerSymbol
from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.player import Player
from py_tic_tac_toe.player_ai import HardAiPlayer, RandomAiPlayer
from py_tic_tac_toe.player_local import LocalPlayer
from py_tic_tac_toe.player_network import LocalNetworkPlayer, RemoteNetworkPlayer
from py_tic_tac_toe.tcp_transport import TcpTransport, create_client_transport, create_host_transport
from py_tic_tac_toe.ui import Ui

# ============================================================================
# Player Factories for Local Mode
# ============================================================================


def _create_local_player(
    player_type: Literal["human", "easy-ai", "hard-ai"],
    symbol: PlayerSymbol,
    game_engine: GameEngine,
    uis: list[Ui],
) -> Player:
    match player_type:
        case "human":
            human_player = LocalPlayer(symbol, game_engine.game)
            for ui in uis:
                human_player.add_enable_input_cb(ui.enable_input)
            return human_player
        case "easy-ai":
            random_ai_player = RandomAiPlayer(symbol, game_engine.game)
            random_ai_player.set_apply_move_cb(game_engine.apply_move)
            return random_ai_player
        case "hard-ai":
            hard_ai_player = HardAiPlayer(symbol, game_engine.game)
            hard_ai_player.set_apply_move_cb(game_engine.apply_move)
            return hard_ai_player
        case _:
            msg = f"Unknown local player type: {player_type}. Choose from 'human', 'easy-ai', 'hard-ai'."
            raise ValueError(msg)


def create_local_players(
    player_x_type: Literal["human", "easy-ai", "hard-ai"],
    player_o_type: Literal["human", "easy-ai", "hard-ai"],
    game_engine: GameEngine,
    uis: list[Ui],
) -> tuple[Player, Player]:
    player1 = _create_local_player(player_x_type, "X", game_engine, uis)
    player2 = _create_local_player(player_o_type, "O", game_engine, uis)
    return player1, player2


# ============================================================================
# Player Factories for Network Mode
# ============================================================================


def _create_network_player(
    player_type: Literal["local", "remote"],
    game_engine: GameEngine,
    uis: list[Ui],
    transport: TcpTransport,
    symbol: PlayerSymbol | None = None,
) -> Player:
    match player_type:
        case "local":
            local_player = LocalNetworkPlayer(game_engine.game, transport, symbol)
            for ui in uis:
                local_player.add_enable_input_cb(ui.enable_input)
            return local_player
        case "remote":
            remote_player = RemoteNetworkPlayer(game_engine.game, transport, symbol)
            remote_player.set_apply_move_cb(game_engine.apply_move)
            return remote_player
        case _:
            msg = f"Unknown network player type: {player_type}. Choose from 'local', 'remote'."
            raise ValueError(msg)


def create_network_host_players(
    player_x_type: Literal["local", "remote"],
    player_o_type: Literal["local", "remote"],
    game_engine: GameEngine,
    uis: list[Ui],
    port: int,
) -> tuple[Player, Player]:
    if player_x_type == player_o_type:
        raise ValueError("Player types must differ in network mode.")
    transport = create_host_transport(port)
    player1 = _create_network_player(player_x_type, game_engine, uis, transport, "X")
    player2 = _create_network_player(player_o_type, game_engine, uis, transport, "O")
    return player1, player2


def create_network_client_players(
    game_engine: GameEngine,
    uis: list[Ui],
    host: str,
    port: int,
) -> tuple[Player, Player]:
    transport = create_client_transport(host, port)
    player1 = _create_network_player("local", game_engine, uis, transport)
    player2 = _create_network_player("remote", game_engine, uis, transport)
    return player1, player2


# ============================================================================
# GameEngine Factories
# ============================================================================


def config_game_engine(game_engine: GameEngine, players: tuple[Player, Player], uis: list[Ui]) -> GameEngine:
    game_engine.set_players(*players)
    for ui in uis:
        game_engine.add_board_updated_cb(ui.on_board_updated)
    return game_engine
