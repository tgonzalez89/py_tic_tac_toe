import socket
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from py_tic_tac_toe.board import Move, PlayerSymbol
from py_tic_tac_toe.exception import InvalidMoveError, NetworkError
from py_tic_tac_toe.factories import _create_network_player, config_game_engine, create_local_players
from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.tcp_transport import TcpTransport, create_client_transport, create_host_transport
from py_tic_tac_toe.ui import Ui


class FakeUI(Ui):
    def __init__(self, game_engine: GameEngine) -> None:
        super().__init__(game_engine)
        self.board_updated_count = 0
        self.end_message: str | None = None
        self.errors: list[Exception] = []

    def run(self) -> None:
        super().run()
        self._game_engine.start()

    def _render_board(self) -> None:
        self.board_updated_count += 1

    def _show_end_message(self, msg: str) -> None:
        self.end_message = msg
        super()._stop()

    def on_error(self, _exception: Exception) -> None:
        self.errors.append(_exception)
        super().on_error(_exception)

    @property
    def board(self) -> list[list[PlayerSymbol | None]]:
        return self._game_engine.game.board.board

    def simulate_move(self, row: int, col: int) -> None:
        if not self._input_enabled:
            raise RuntimeError("Input is not enabled - cannot move now")
        self._queue_move(row, col)
        self._game_engine.tick()


# ============================================================================
# HAPPY PATH TESTS - Local Games
# ============================================================================


def create_local_human_vs_human() -> tuple[GameEngine, FakeUI]:
    game_engine = GameEngine()
    ui = FakeUI(game_engine)
    player1, player2 = create_local_players("human", "human", game_engine.game.board, [ui])
    config_game_engine(game_engine, (player1, player2), [ui])
    return game_engine, ui


class TestLocalHumanVsHuman:
    """Test local human vs human game."""

    def test_complete_game_human_vs_human(self) -> None:
        """Test a human player vs human player game with predefined moves."""
        _game_engine, ui = create_local_human_vs_human()

        assert not ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert not ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 0

        ui.run()

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 1

        # Simulate a game: X wins with diagonal

        # X at (0, 0)
        ui.simulate_move(0, 0)

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "O"
        assert ui.board_updated_count == 2
        assert ui.board[0][0] == "X"

        # O at (1, 0)
        ui.simulate_move(1, 0)

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 3
        assert ui.board[1][0] == "O"

        # X at (1, 1)
        ui.simulate_move(1, 1)

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "O"
        assert ui.board_updated_count == 4
        assert ui.board[1][1] == "X"

        # O at (0, 1)
        ui.simulate_move(0, 1)

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 5
        assert ui.board[0][1] == "O"

        # X at (2, 2) - X wins
        ui.simulate_move(2, 2)

        assert not ui._running
        assert ui.end_message is not None and "Winner: X" in ui.end_message
        assert ui._game_engine.game.board.is_game_over()
        assert not ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "O"
        assert ui.board_updated_count == 6
        assert ui.board[2][2] == "X"

        assert ui._game_engine.game.board.get_winner() == "X"
        assert not ui._game_engine.game.board.is_draw()
        assert not ui._game_engine.game.board.is_full()


class TestLocalHumanVsAI:
    """Test local human vs AI game."""

    def test_human_vs_random_ai(self) -> None:
        """Test human player vs random AI."""
        game_engine = GameEngine()
        ui = FakeUI(game_engine)
        player1, player2 = create_local_players("human", "easy-ai", game_engine.game.board, [ui])
        config_game_engine(game_engine, (player1, player2), [ui])

        assert not ui._running
        assert ui.end_message is None
        assert not ui._input_enabled
        assert not ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 0

        ui.run()

        assert ui._running
        assert ui.end_message is None
        assert ui._input_enabled
        assert not ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 1

        # Simulate a game

        # Human plays X
        ui.simulate_move(0, 0)

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert not ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "O"
        assert ui.board_updated_count == 2
        assert ui.board[0][0] == "X"

        # AI plays O
        game_engine.tick()

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 3
        assert sum(1 for row in ui.board for cell in row if cell == "X") == 1
        assert sum(1 for row in ui.board for cell in row if cell == "O") == 1

        # Play until game is done
        while not ui._game_engine.game.board.is_game_over():
            # Human
            available = game_engine.game.board.get_available_positions()
            if available:
                row, col = available[0]
                ui.simulate_move(row, col)
            # Break early if game ended after previous move
            if ui._game_engine.game.board.is_game_over():
                break
            # AI
            game_engine.tick()

        assert not ui._running
        assert ui.end_message is not None
        assert ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0

        if "Winner:" in ui.end_message:
            assert ui._game_engine.game.board.get_winner() is not None
            assert not ui._game_engine.game.board.is_draw()
        else:
            assert ui._game_engine.game.board.get_winner() is None
            assert ui._game_engine.game.board.is_draw()
            assert ui._game_engine.game.board.is_full()

    def test_random_ai_vs_human(self) -> None:
        """Test random AI vs human player."""
        game_engine = GameEngine()
        ui = FakeUI(game_engine)
        player1, player2 = create_local_players("easy-ai", "human", game_engine.game.board, [ui])
        config_game_engine(game_engine, (player1, player2), [ui])

        assert not ui._running
        assert ui.end_message is None
        assert not ui._input_enabled
        assert not ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 0

        ui.run()

        assert ui._running
        assert ui.end_message is None
        assert not ui._input_enabled
        assert not ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 1

        # Simulate a game

        # AI plays X
        game_engine.tick()

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "O"
        assert ui.board_updated_count == 2
        assert sum(1 for row in ui.board for cell in row if cell == "X") == 1
        assert sum(1 for row in ui.board for cell in row if cell == "O") == 0

        # Human plays O
        available = game_engine.game.board.get_available_positions()
        row, col = available[0]
        ui.simulate_move(row, col)

        assert ui._running
        assert ui.end_message is None
        assert not ui._game_engine.game.board.is_game_over()
        assert not ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 3
        assert ui.board[row][col] == "O"

        # Play until game is done
        while not ui._game_engine.game.board.is_game_over():
            # AI
            game_engine.tick()
            # Break early if game ended after previous move
            if ui._game_engine.game.board.is_game_over():
                break
            # Human
            available = game_engine.game.board.get_available_positions()
            if available:
                row, col = available[0]
                ui.simulate_move(row, col)

        assert not ui._running
        assert ui.end_message is not None
        assert ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0

        if "Winner:" in ui.end_message:
            assert ui._game_engine.game.board.get_winner() is not None
            assert not ui._game_engine.game.board.is_draw()
        else:
            assert ui._game_engine.game.board.get_winner() is None
            assert ui._game_engine.game.board.is_draw()
            assert ui._game_engine.game.board.is_full()


class TestLocalAIVsAI:
    """Test local AI vs AI game."""

    def test_random_ai_vs_random_ai(self) -> None:
        """Test random AI vs random AI game."""
        game_engine = GameEngine()
        ui = FakeUI(game_engine)
        player1, player2 = create_local_players("easy-ai", "easy-ai", game_engine.game.board, [ui])
        config_game_engine(game_engine, (player1, player2), [ui])

        assert not ui._running
        assert ui.end_message is None
        assert not ui._input_enabled
        assert not ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 0

        ui.run()

        assert ui._running
        assert ui.end_message is None
        assert not ui._input_enabled
        assert not ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 1

        # Play until game is done
        while not ui._game_engine.game.board.is_game_over():
            game_engine.tick()

        assert not ui._running
        assert ui.end_message is not None
        assert ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0

        if "Winner:" in ui.end_message:
            assert ui._game_engine.game.board.get_winner() is not None
            assert not ui._game_engine.game.board.is_draw()
        else:
            assert ui._game_engine.game.board.get_winner() is None
            assert ui._game_engine.game.board.is_draw()
            assert ui._game_engine.game.board.is_full()

    def test_hard_ai_vs_hard_ai(self) -> None:
        """Test hard AI vs hard AI game - should always result in a draw."""
        game_engine = GameEngine()
        ui = FakeUI(game_engine)
        player1, player2 = create_local_players("hard-ai", "hard-ai", game_engine.game.board, [ui])
        config_game_engine(game_engine, (player1, player2), [ui])

        assert not ui._running
        assert ui.end_message is None
        assert not ui._input_enabled
        assert not ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 0

        ui.run()

        assert ui._running
        assert ui.end_message is None
        assert not ui._input_enabled
        assert not ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "X"
        assert ui.board_updated_count == 1

        # Play until game is done
        while not ui._game_engine.game.board.is_game_over():
            game_engine.tick()

        assert not ui._running
        assert ui.end_message is not None and "draw" in ui.end_message
        assert ui._game_engine.game.board.is_game_over()
        assert len(ui.errors) == 0

        assert ui._game_engine.game.board.get_winner() is None
        assert ui._game_engine.game.board.is_draw()
        assert ui._game_engine.game.board.is_full()


# ============================================================================
# HAPPY PATH TESTS - Network Games
# ============================================================================


def create_network_human_vs_human() -> tuple[FakeUI, FakeUI, TcpTransport, TcpTransport]:
    game_engine_host = GameEngine()
    game_engine_client = GameEngine()

    ui_host = FakeUI(game_engine_host)
    ui_client = FakeUI(game_engine_client)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])

    # Create transports first (they block each other, so use ThreadPool)
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_host = executor.submit(create_host_transport, port)
        future_client = executor.submit(create_client_transport, "127.0.0.1", port)
        transport_host: TcpTransport = future_host.result()
        transport_client: TcpTransport = future_client.result()

    # Create host players first (non-blocking, just send symbol assignment messages)
    player1_host = _create_network_player(
        "local",
        [ui_host],
        transport_host,
        game_engine_host,
        "X",
    )
    player2_host = _create_network_player(
        "remote",
        [ui_host],
        transport_host,
        game_engine_host,
        "O",
    )

    # Create client players (may block briefly waiting for host symbols, but host is ready)
    player1_client = _create_network_player(
        "remote",
        [ui_client],
        transport_client,
        game_engine_client,
    )
    player2_client = _create_network_player(
        "local",
        [ui_client],
        transport_client,
        game_engine_client,
    )

    # Configure game engines
    config_game_engine(game_engine_host, (player1_host, player2_host), [ui_host])
    config_game_engine(game_engine_client, (player1_client, player2_client), [ui_client])

    return ui_host, ui_client, transport_host, transport_client


def close_transports(*transports: TcpTransport) -> None:
    for transport in transports:
        transport._close()


def wait_for_board_updates(
    ui_host: FakeUI,
    ui_client: FakeUI,
    expected_updates_host: int,
    expected_updates_client: int,
    timeout: float = 2.0,
) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if (
            ui_host.board_updated_count >= expected_updates_host
            and ui_client.board_updated_count >= expected_updates_client
        ):
            return
        ui_host._game_engine.tick()
        ui_client._game_engine.tick()
        time.sleep(0.01)

    error_msg = (
        f"Board updates timeout: host={ui_host.board_updated_count}/{expected_updates_host}, "
        f"client={ui_client.board_updated_count}/{expected_updates_client}"
    )
    raise TimeoutError(error_msg)


class TestNetworkHumanVsHuman:
    """Test network-based human vs human game."""

    def test_network_human_vs_human_complete_game(self) -> None:
        """Test a complete network human vs human game."""
        ui_host, ui_client, transport_host, transport_client = create_network_human_vs_human()

        try:
            assert not ui_host._running
            assert ui_host.end_message is None
            assert not ui_host._input_enabled
            assert not ui_host._game_engine.game.board.is_game_over()
            assert len(ui_host.errors) == 0
            assert ui_host._game_engine.game._current_player_symbol == "X"
            assert ui_host.board_updated_count == 0

            assert not ui_client._running
            assert ui_client.end_message is None
            assert not ui_client._input_enabled
            assert not ui_client._game_engine.game.board.is_game_over()
            assert len(ui_client.errors) == 0
            assert ui_client._game_engine.game._current_player_symbol == "X"
            assert ui_client.board_updated_count == 0

            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            assert ui_host._running
            assert ui_host.end_message is None
            assert not ui_host._game_engine.game.board.is_game_over()
            assert ui_host._input_enabled
            assert len(ui_host.errors) == 0
            assert ui_host._game_engine.game._current_player_symbol == "X"
            assert ui_host.board_updated_count == 1

            assert ui_client._running
            assert ui_client.end_message is None
            assert not ui_client._game_engine.game.board.is_game_over()
            assert not ui_client._input_enabled
            assert len(ui_client.errors) == 0
            assert ui_client._game_engine.game._current_player_symbol == "X"
            assert ui_client.board_updated_count == 1

            # Simulate a game: X wins with diagonal

            # Player X (local on host, remote on client) makes first move at (0, 0)
            ui_host.simulate_move(0, 0)
            wait_for_board_updates(ui_host, ui_client, 2, 2)

            assert ui_host._running
            assert ui_host.end_message is None
            assert not ui_host._game_engine.game.board.is_game_over()
            assert not ui_host._input_enabled
            assert len(ui_host.errors) == 0
            assert ui_host._game_engine.game._current_player_symbol == "O"
            assert ui_host.board_updated_count == 2
            assert ui_host.board[0][0] == "X"

            assert ui_client._running
            assert ui_client.end_message is None
            assert not ui_client._game_engine.game.board.is_game_over()
            assert ui_client._input_enabled
            assert len(ui_client.errors) == 0
            assert ui_client._game_engine.game._current_player_symbol == "O"
            assert ui_client.board_updated_count == 2
            assert ui_client.board[0][0] == "X"

            # Player O (local on client, remote on host) makes second move at (1, 0)
            ui_client.simulate_move(1, 0)
            wait_for_board_updates(ui_host, ui_client, 3, 3)

            assert ui_host._running
            assert ui_host.end_message is None
            assert not ui_host._game_engine.game.board.is_game_over()
            assert ui_host._input_enabled
            assert len(ui_host.errors) == 0
            assert ui_host._game_engine.game._current_player_symbol == "X"
            assert ui_host.board_updated_count == 3
            assert ui_host.board[1][0] == "O"

            assert ui_client._running
            assert ui_client.end_message is None
            assert not ui_client._game_engine.game.board.is_game_over()
            assert not ui_client._input_enabled
            assert len(ui_client.errors) == 0
            assert ui_client._game_engine.game._current_player_symbol == "X"
            assert ui_client.board_updated_count == 3
            assert ui_client.board[1][0] == "O"

            # X at (1, 1)
            ui_host.simulate_move(1, 1)
            wait_for_board_updates(ui_host, ui_client, 4, 4)

            assert ui_host._running
            assert ui_host.end_message is None
            assert not ui_host._game_engine.game.board.is_game_over()
            assert not ui_host._input_enabled
            assert len(ui_host.errors) == 0
            assert ui_host._game_engine.game._current_player_symbol == "O"
            assert ui_host.board_updated_count == 4
            assert ui_host.board[1][1] == "X"

            assert ui_client._running
            assert ui_client.end_message is None
            assert not ui_client._game_engine.game.board.is_game_over()
            assert ui_client._input_enabled
            assert len(ui_client.errors) == 0
            assert ui_client._game_engine.game._current_player_symbol == "O"
            assert ui_client.board_updated_count == 4
            assert ui_client.board[1][1] == "X"

            # O at (0, 1)
            ui_client.simulate_move(0, 1)
            wait_for_board_updates(ui_host, ui_client, 5, 5)

            assert ui_host._running
            assert ui_host.end_message is None
            assert not ui_host._game_engine.game.board.is_game_over()
            assert ui_host._input_enabled
            assert len(ui_host.errors) == 0
            assert ui_host._game_engine.game._current_player_symbol == "X"
            assert ui_host.board_updated_count == 5
            assert ui_host.board[0][1] == "O"

            assert ui_client._running
            assert ui_client.end_message is None
            assert not ui_client._game_engine.game.board.is_game_over()
            assert not ui_client._input_enabled
            assert len(ui_client.errors) == 0
            assert ui_client._game_engine.game._current_player_symbol == "X"
            assert ui_client.board_updated_count == 5
            assert ui_client.board[0][1] == "O"

            # X at (2, 2) - X wins
            ui_host.simulate_move(2, 2)
            wait_for_board_updates(ui_host, ui_client, 6, 6)

            assert not ui_host._running
            assert ui_host.end_message is not None and "Winner: X" in ui_host.end_message
            assert ui_host._game_engine.game.board.is_game_over()
            assert not ui_host._input_enabled
            assert len(ui_host.errors) == 0
            assert ui_host._game_engine.game._current_player_symbol == "O"
            assert ui_host.board_updated_count == 6
            assert ui_host.board[2][2] == "X"

            assert not ui_client._running
            assert ui_client.end_message is not None and "Winner: X" in ui_client.end_message
            assert ui_client._game_engine.game.board.is_game_over()
            assert not ui_client._input_enabled
            assert len(ui_client.errors) == 0
            assert ui_client._game_engine.game._current_player_symbol == "O"
            assert ui_client.board_updated_count == 6
            assert ui_client.board[2][2] == "X"

            assert ui_host._game_engine.game.board.get_winner() == "X"
            assert not ui_host._game_engine.game.board.is_draw()
            assert not ui_host._game_engine.game.board.is_full()

            assert ui_client._game_engine.game.board.get_winner() == "X"
            assert not ui_client._game_engine.game.board.is_draw()
            assert not ui_client._game_engine.game.board.is_full()

        finally:
            close_transports(transport_host, transport_client)


# ============================================================================
# ERROR HANDLING TESTS - Local Games
# ============================================================================


class TestLocalHumanVsHumanErrorHandling:
    """Test error handling in local human vs human game."""

    def test_illegal_move_occupied_cell(self) -> None:
        """Test that occupied cell move is rejected."""
        _game_engine, ui = create_local_human_vs_human()

        ui.run()

        # Valid move
        ui.simulate_move(0, 0)
        assert len(ui.errors) == 0
        assert ui.board[0][0] == "X"

        # Invalid move - cell occupied
        ui.simulate_move(0, 0)
        assert len(ui.errors) == 1
        assert isinstance(ui.errors[0], InvalidMoveError)
        assert "Cell occupied" in str(ui.errors[0])
        assert ui.board[0][0] == "X"

    def test_illegal_move_out_of_bounds(self) -> None:
        """Test that out of bounds move is rejected."""
        _game_engine, ui = create_local_human_vs_human()

        ui.run()

        # Invalid move - out of bounds
        ui.simulate_move(4, 4)
        assert len(ui.errors) == 1
        assert isinstance(ui.errors[0], IndexError)
        assert "Move out of bounds" in str(ui.errors[0])

    def test_cannot_move_when_input_disabled(self) -> None:
        """Test that moves are rejected when input is disabled."""
        _game_engine, ui = create_local_human_vs_human()

        ui.run()

        # Manually disable input to simulate waiting for other player
        ui._disable_input()

        # Try to move while input is disabled
        with pytest.raises(RuntimeError, match="Input is not enabled"):
            ui.simulate_move(0, 0)

    def test_cannot_move_when_not_current_player_turn(self) -> None:
        """Test that moves are rejected when it's not the current player's turn."""
        game_engine, ui = create_local_human_vs_human()

        ui.run()

        # Player 1 (X) makes a move
        ui.simulate_move(0, 0)
        assert ui.board[0][0] == "X"

        # Player 2 (O) makes a move
        ui.simulate_move(1, 0)
        assert ui.board[1][0] == "O"

        # Apply a valid move for the player whose turn it is not
        available = game_engine.game.board.get_available_positions()
        row, col = available[0]
        with pytest.raises(InvalidMoveError, match="Not your turn"):
            game_engine.game.apply_move(Move("O", row, col))

    def test_cannot_move_after_game_ends(self) -> None:
        """Test that no moves are allowed after the game has ended."""
        game_engine, ui = create_local_human_vs_human()

        ui.run()

        # Play a complete game: X wins with diagonal
        # X at (0, 0)
        ui.simulate_move(0, 0)
        # O at (1, 0)
        ui.simulate_move(1, 0)
        # X at (1, 1)
        ui.simulate_move(1, 1)
        # O at (0, 1)
        ui.simulate_move(0, 1)
        # X at (2, 2) - X wins
        ui.simulate_move(2, 2)

        # Game should be finished
        assert not ui._running
        assert ui.end_message is not None and "Winner: X" in ui.end_message
        assert ui._game_engine.game.board.is_game_over()
        assert not ui._input_enabled
        assert len(ui.errors) == 0
        assert ui._game_engine.game._current_player_symbol == "O"
        assert ui.board_updated_count == 6
        assert ui.board[2][2] == "X"

        # Try to apply a move after game has ended
        available = game_engine.game.board.get_available_positions()
        row, col = available[0]
        with pytest.raises(InvalidMoveError, match="Game over"):
            game_engine.game.apply_move(Move("O", row, col))


# ============================================================================
# ERROR HANDLING TESTS - Network Games
# ============================================================================


class TestNetworkHumanVsHumanErrorHandling:
    """Test error handling in network-based human vs human game."""

    def test_client_cannot_move_before_host_turn(self) -> None:
        ui_host, ui_client, transport_host, transport_client = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            with pytest.raises(RuntimeError, match="Input is not enabled"):
                ui_client.simulate_move(0, 0)

            assert ui_host.board[0][0] is None
            assert ui_client.board[0][0] is None

            assert len(ui_host.errors) == 0
            assert len(ui_client.errors) == 0
        finally:
            close_transports(transport_host, transport_client)

    def test_host_cannot_move_when_not_turn(self) -> None:
        ui_host, ui_client, transport_host, transport_client = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            ui_host.simulate_move(0, 0)
            wait_for_board_updates(ui_host, ui_client, 2, 2)

            with pytest.raises(RuntimeError, match="Input is not enabled"):
                ui_host.simulate_move(0, 1)

            assert ui_host.board[0][1] is None
            assert ui_client.board[0][1] is None

            assert len(ui_host.errors) == 0
            assert len(ui_client.errors) == 0
        finally:
            close_transports(transport_host, transport_client)

    def test_client_move_after_host_disconnect(self) -> None:
        ui_host, ui_client, transport_host, transport_client = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            ui_host.simulate_move(0, 0)
            wait_for_board_updates(ui_host, ui_client, 2, 2)

            transport_host._close()

            # Wait for transport_client to also be closed
            # Wait for running flag to be cleared, which indicates the transport is shutting down
            while transport_client._running:
                time.sleep(0.01)
            # Wait for lock to be released, it means the transport has fully shut down
            with transport_client._close_lock:
                pass

            with pytest.raises(NetworkError):
                ui_client.simulate_move(1, 0)

            # With async design, move is applied locally without waiting for remote confirmation
            # The move will succeed locally if send doesn't immediately fail
            # This test demonstrates the new async behavior where moves can be applied
            # locally even when remote is disconnected

            # Check if an error was detected (might not be immediate)
            if len(ui_client.errors) > 0:
                assert isinstance(ui_client.errors[0], NetworkError)

            # Move may be applied locally on client side with async design
            # since we don't wait for acknowledgement
        finally:
            close_transports(transport_host, transport_client)

    def test_host_move_after_client_disconnect(self) -> None:
        ui_host, ui_client, transport_host, transport_client = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            transport_client._close()

            # Wait for transport_host to also be closed
            # Wait for running flag to be cleared, which indicates the transport is shutting down
            while transport_host._running:
                time.sleep(0.01)
            # Wait for lock to be released, it means the transport has fully shut down
            with transport_host._close_lock:
                pass

            with pytest.raises(NetworkError):
                ui_host.simulate_move(0, 0)

            # With async design, move is applied locality without waiting for remote confirmation
            # The move will succeed locally if send doesn't immediately fail
            # This test demonstrates the new async behavior where moves can be applied
            # locally even when remote is disconnected

            # Check if an error was detected (might not be immediate)
            if len(ui_host.errors) > 0:
                assert isinstance(ui_host.errors[0], NetworkError)

            # Move may be applied locally on host side with async design
            # since we don't wait for acknowledgement
        finally:
            close_transports(transport_host, transport_client)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
