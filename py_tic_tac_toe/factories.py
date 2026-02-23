"""Factory functions for creating game components.

Provides factories for creating:
- Players (local human, AI, network)
- Game engines
- UIs (terminal, pygame, tk)
- Complete game setups
"""

from typing import Literal

from py_tic_tac_toe.board import PlayerSymbol
from py_tic_tac_toe.game import Game
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
    game: Game,
    uis: list[Ui],
) -> Player:
    match player_type:
        case "human":
            human_player = LocalPlayer(game, symbol)
            for ui in uis:
                human_player.add_enable_input_cb(ui.enable_input)
            return human_player
        case "easy-ai":
            return RandomAiPlayer(game, symbol)
        case "hard-ai":
            return HardAiPlayer(game, symbol)
        case _:
            msg = f"Unknown local player type: {player_type}. Choose from 'human', 'easy-ai', 'hard-ai'."
            raise ValueError(msg)


def create_local_players(
    player_x_type: Literal["human", "easy-ai", "hard-ai"],
    player_o_type: Literal["human", "easy-ai", "hard-ai"],
    game: Game,
    uis: list[Ui],
) -> tuple[Player, Player]:
    player1 = _create_local_player(player_x_type, "X", game, uis)
    player2 = _create_local_player(player_o_type, "O", game, uis)
    return player1, player2


# ============================================================================
# Player Factories for Network Mode
# ============================================================================


def _create_network_player(
    player_type: Literal["local", "remote"],
    uis: list[Ui],
    transport: TcpTransport,
    game: Game,
    symbol: PlayerSymbol | None = None,
) -> Player:
    match player_type:
        case "local":
            local_player = LocalNetworkPlayer(game, transport, symbol)
            for ui in uis:
                local_player.add_enable_input_cb(ui.enable_input)
                local_player.add_on_error_cb(ui.on_error)
            return local_player
        case "remote":
            remote_player = RemoteNetworkPlayer(game, transport, symbol)
            for ui in uis:
                remote_player.add_on_error_cb(ui.on_error)
            return remote_player
        case _:
            msg = f"Unknown network player type: {player_type}. Choose from 'local', 'remote'."
            raise ValueError(msg)


def create_network_host_players(
    player_x_type: Literal["local", "remote"],
    player_o_type: Literal["local", "remote"],
    uis: list[Ui],
    game: Game,
    port: int,
) -> tuple[Player, Player]:
    if player_x_type == player_o_type:
        raise ValueError("Player types must differ in network mode.")
    transport = create_host_transport(port)
    player1 = _create_network_player(player_x_type, uis, transport, game, "X")
    player2 = _create_network_player(player_o_type, uis, transport, game, "O")
    return player1, player2


def create_network_client_players(
    uis: list[Ui],
    game: Game,
    host: str,
    port: int,
) -> tuple[Player, Player]:
    transport = create_client_transport(host, port)
    player1 = _create_network_player("local", uis, transport, game)
    player2 = _create_network_player("remote", uis, transport, game)
    return player1, player2


# ============================================================================
# GameEngine Factories
# ============================================================================


def config_game_engine(game_engine: GameEngine, players: tuple[Player, Player], uis: list[Ui]) -> GameEngine:
    game_engine.set_players(*players)
    for ui in uis:
        game_engine.add_board_updated_cb(ui.on_board_updated)
        game_engine.add_on_error_cb(ui.on_error)

    return game_engine
