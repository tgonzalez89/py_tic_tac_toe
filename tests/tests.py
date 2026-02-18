import socket
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from py_tic_tac_toe.board import Move, PlayerSymbol
from py_tic_tac_toe.exception import InvalidMoveError
from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.player_ai import RandomAiPlayer
from py_tic_tac_toe.player_local import LocalPlayer
from py_tic_tac_toe.player_network import LocalNetworkPlayer, RemoteNetworkPlayer
from py_tic_tac_toe.tcp_transport import TcpTransport, create_client_transport, create_host_transport
from py_tic_tac_toe.ui import Ui


class FakeUI(Ui):
    """Fake UI implementation for testing."""

    def __init__(self, game_engine: GameEngine) -> None:
        super().__init__(game_engine)
        self.board_updated_count = 0
        self.end_message: str | None = None
        self.input_errors: list[Exception] = []
        self.game_finished = False

    def run(self) -> None:
        """Start the game."""
        super().run()
        self._game_engine.start()

    def _render_board(self) -> None:
        """Track board updates."""
        self.board_updated_count += 1

    def _show_end_message(self, message: str) -> None:
        """Track end game message."""
        self.end_message = message
        self.game_finished = True

    def on_input_error(self, exception: Exception) -> None:
        """Track input errors."""
        self.input_errors.append(exception)

    def get_board_state(self) -> list[list[PlayerSymbol | None]]:
        """Get current board state."""
        return self._game_engine.game.board.board

    def simulate_move(self, row: int, col: int) -> None:
        """Simulate a user input move (for local players)."""
        if not self._input_enabled:
            raise RuntimeError("Input is not enabled - cannot move now")
        self._apply_move(row, col)


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def create_local_human_vs_human() -> tuple[GameEngine, FakeUI, LocalPlayer, LocalPlayer]:
    game_engine = GameEngine()
    ui = FakeUI(game_engine)

    player1 = LocalPlayer("X", game_engine.game)
    player2 = LocalPlayer("O", game_engine.game)

    player1.add_enable_input_cb(ui.enable_input)
    player1.add_input_error_cb(ui.on_input_error)
    player2.add_enable_input_cb(ui.enable_input)
    player2.add_input_error_cb(ui.on_input_error)

    game_engine.set_players(player1, player2)
    game_engine.add_board_updated_cb(ui.on_board_updated)

    return game_engine, ui, player1, player2


def create_network_human_vs_human() -> tuple[
    GameEngine,
    GameEngine,
    FakeUI,
    FakeUI,
    TcpTransport,
    TcpTransport,
]:
    game_engine_host = GameEngine()
    game_engine_client = GameEngine()

    ui_host = FakeUI(game_engine_host)
    ui_client = FakeUI(game_engine_client)

    port = get_free_port()
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_host = executor.submit(create_host_transport, port)
        future_client = executor.submit(create_client_transport, "127.0.0.1", port)
        while not (future_host.done() and future_client.done()):
            time.sleep(0.01)
        transport_host: TcpTransport = future_host.result()
        transport_client: TcpTransport = future_client.result()

    player1_host = LocalNetworkPlayer(game_engine_host.game, transport_host, "X")
    player2_host = RemoteNetworkPlayer(game_engine_host.game, transport_host, "O")

    player1_client = RemoteNetworkPlayer(game_engine_client.game, transport_client)
    player2_client = LocalNetworkPlayer(game_engine_client.game, transport_client)

    player1_host.add_enable_input_cb(ui_host.enable_input)
    player1_host.add_input_error_cb(ui_host.on_input_error)
    player2_host.set_apply_move_cb(game_engine_host.apply_move)

    player1_client.set_apply_move_cb(game_engine_client.apply_move)
    player2_client.add_enable_input_cb(ui_client.enable_input)
    player2_client.add_input_error_cb(ui_client.on_input_error)

    game_engine_host.set_players(player1_host, player2_host)
    game_engine_host.add_board_updated_cb(ui_host.on_board_updated)

    game_engine_client.set_players(player1_client, player2_client)
    game_engine_client.add_board_updated_cb(ui_client.on_board_updated)

    return (
        game_engine_host,
        game_engine_client,
        ui_host,
        ui_client,
        transport_host,
        transport_client,
    )


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
    """Wait until both UIs have received the expected number of board updates.

    Args:
        ui_host: Host UI instance
        ui_client: Client UI instance
        expected_updates_host: Expected board_updated_count on host
        expected_updates_client: Expected board_updated_count on client
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If updates don't arrive within timeout

    """
    start = time.time()
    while time.time() - start < timeout:
        if (
            ui_host.board_updated_count >= expected_updates_host
            and ui_client.board_updated_count >= expected_updates_client
        ):
            return
        time.sleep(0.01)

    error_msg = (
        f"Board updates timeout: host={ui_host.board_updated_count}/{expected_updates_host}, "
        f"client={ui_client.board_updated_count}/{expected_updates_client}"
    )
    raise TimeoutError(error_msg)


# ============================================================================
# HAPPY PATH TESTS - Local Games
# ============================================================================


class TestLocalHumanVsHuman:
    """Test local human vs human game."""

    def test_complete_game_human_vs_human(self) -> None:
        """Test a human player vs human player game with predefined moves."""
        _game_engine, ui, _player1, _player2 = create_local_human_vs_human()

        ui.run()

        # Simulate a game: X wins with diagonal
        # X at (0, 0)
        assert ui._input_enabled
        ui.simulate_move(0, 0)
        # Input is re-enabled for next player (O)
        assert ui._input_enabled
        assert ui.get_board_state()[0][0] == "X"

        # O at (1, 0)
        ui.simulate_move(1, 0)
        assert ui._input_enabled
        assert ui.get_board_state()[1][0] == "O"

        # X at (1, 1)
        ui.simulate_move(1, 1)
        assert ui._input_enabled
        assert ui.get_board_state()[1][1] == "X"

        # O at (0, 1)
        ui.simulate_move(0, 1)
        assert ui._input_enabled
        assert ui.get_board_state()[0][1] == "O"

        # X at (2, 2) - X wins
        ui.simulate_move(2, 2)

        # Game should be finished
        assert ui.game_finished
        assert ui.end_message is not None
        assert "Winner: X" in ui.end_message
        assert len(ui.input_errors) == 0


class TestLocalHumanVsAI:
    """Test local human vs AI game."""

    def test_human_vs_random_ai(self) -> None:
        """Test human player vs random AI."""
        game_engine = GameEngine()
        ui = FakeUI(game_engine)

        player1 = LocalPlayer("X", game_engine.game)
        player2 = RandomAiPlayer("O", game_engine.game)

        player1.add_enable_input_cb(ui.enable_input)
        player1.add_input_error_cb(ui.on_input_error)
        player2.set_apply_move_cb(game_engine.apply_move)

        game_engine.set_players(player1, player2)
        game_engine.add_board_updated_cb(ui.on_board_updated)

        ui.run()

        # Simulate game by manually playing moves
        # Human plays X
        ui.simulate_move(0, 0)

        # Check that both X and O have moved
        board = ui.get_board_state()
        x_count = sum(1 for row in board for cell in row if cell == "X")
        o_count = sum(1 for row in board for cell in row if cell == "O")
        assert x_count == 1
        assert o_count == 1

        # Play until game is done
        while not ui.game_finished:
            available = game_engine.game.board.get_available_positions()
            if available and ui._input_enabled:
                row, col = available[0]
                ui.simulate_move(row, col)

        # Game should finish
        assert ui.game_finished
        assert ui.end_message is not None
        assert "Winner:" in ui.end_message or "draw" in ui.end_message
        assert len(ui.input_errors) == 0


class TestLocalAIVsHuman:
    """Test local AI vs human game."""

    def test_random_ai_vs_human(self) -> None:
        """Test random AI vs human player."""
        game_engine = GameEngine()
        ui = FakeUI(game_engine)

        player1 = RandomAiPlayer("X", game_engine.game)
        player2 = LocalPlayer("O", game_engine.game)

        player1.set_apply_move_cb(game_engine.apply_move)
        player2.add_enable_input_cb(ui.enable_input)
        player2.add_input_error_cb(ui.on_input_error)

        game_engine.set_players(player1, player2)
        game_engine.add_board_updated_cb(ui.on_board_updated)

        ui.run()

        # AI starts first and makes a move automatically
        board = ui.get_board_state()
        x_count = sum(1 for row in board for cell in row if cell == "X")
        o_count = sum(1 for row in board for cell in row if cell == "O")
        assert x_count == 1
        assert o_count == 0

        # Human plays
        available = game_engine.game.board.get_available_positions()
        row, col = available[0]
        ui.simulate_move(row, col)
        board = ui.get_board_state()
        x_count = sum(1 for row in board for cell in row if cell == "X")
        o_count = sum(1 for row in board for cell in row if cell == "O")
        assert x_count == 2
        assert o_count == 1

        # Continue to game end
        while not ui.game_finished:
            available = game_engine.game.board.get_available_positions()
            if available and ui._input_enabled:
                row, col = available[0]
                ui.simulate_move(row, col)

        assert ui.game_finished
        assert ui.end_message is not None
        assert "Winner:" in ui.end_message or "draw" in ui.end_message
        assert len(ui.input_errors) == 0


class TestLocalAIVsAI:
    """Test local AI vs AI game."""

    def test_random_ai_vs_random_ai(self) -> None:
        """Test random AI vs random AI game."""
        game_engine = GameEngine()
        ui = FakeUI(game_engine)

        player1 = RandomAiPlayer("X", game_engine.game)
        player2 = RandomAiPlayer("O", game_engine.game)

        player1.set_apply_move_cb(game_engine.apply_move)
        player2.set_apply_move_cb(game_engine.apply_move)

        game_engine.set_players(player1, player2)
        game_engine.add_board_updated_cb(ui.on_board_updated)

        ui.run()

        # AI vs AI game completes automatically through callback chain
        # Just wait for it to finish or timeout
        timeout = time.time() + 5
        while not ui.game_finished and time.time() < timeout:
            time.sleep(0.01)

        assert ui.game_finished
        assert ui.end_message is not None
        assert "Winner:" in ui.end_message or "draw" in ui.end_message
        assert len(ui.input_errors) == 0


# ============================================================================
# HAPPY PATH TESTS - Network Games
# ============================================================================


class TestNetworkHumanVsHuman:
    """Test network-based human vs human game."""

    def test_network_human_vs_human_complete_game(self) -> None:
        """Test a complete network human vs human game."""
        (
            _game_engine_host,
            _game_engine_client,
            ui_host,
            ui_client,
            transport_host,
            transport_client,
        ) = create_network_human_vs_human()

        try:
            # Start games
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            # Player 1 (local on host, X) makes first move
            ui_host.simulate_move(0, 0)
            # Wait for move to propagate
            wait_for_board_updates(ui_host, ui_client, 2, 2)
            assert ui_host.get_board_state()[0][0] == "X"
            assert ui_client.get_board_state()[0][0] == "X"

            # Player 2 (local on client, O) makes second move
            ui_client.simulate_move(1, 0)
            # Wait for move to propagate
            wait_for_board_updates(ui_host, ui_client, 3, 3)
            assert ui_client.get_board_state()[1][0] == "O"
            assert ui_host.get_board_state()[1][0] == "O"

            # X
            ui_host.simulate_move(1, 1)
            wait_for_board_updates(ui_host, ui_client, 4, 4)

            # O
            ui_client.simulate_move(0, 1)
            wait_for_board_updates(ui_host, ui_client, 5, 5)

            # X wins
            ui_host.simulate_move(2, 2)
            wait_for_board_updates(ui_host, ui_client, 6, 6)

            # Both games should be finished eventually
            timeout = time.time() + 5
            while (not ui_host.game_finished or not ui_client.game_finished) and time.time() < timeout:
                time.sleep(0.01)

            assert ui_host.game_finished, f"Side 1 game not finished, end_message: {ui_host.end_message}"
            assert ui_client.game_finished, f"Side 2 game not finished, end_message: {ui_client.end_message}"
            assert ui_host.end_message is not None and "Winner: X" in ui_host.end_message
            assert ui_client.end_message is not None and "Winner: X" in ui_client.end_message
        finally:
            close_transports(transport_host, transport_client)


# ============================================================================
# ERROR HANDLING TESTS - Local Games
# ============================================================================


class TestLocalHumanVsHumanErrorHandling:
    """Test error handling in local human vs human game."""

    def test_illegal_move_occupied_cell(self) -> None:
        """Test that occupied cell move is rejected."""
        _game_engine, ui, _player1, _player2 = create_local_human_vs_human()

        ui.run()

        # Valid move
        ui.simulate_move(0, 0)
        assert ui.get_board_state()[0][0] == "X"
        assert len(ui.input_errors) == 0

        # Try to place on same cell
        ui.simulate_move(0, 0)

        # Should get an error
        assert len(ui.input_errors) == 1
        assert isinstance(ui.input_errors[0], InvalidMoveError)
        assert "Cell occupied" in str(ui.input_errors[0])

        # Board should not have changed
        assert ui.get_board_state()[0][0] == "X"

    def test_illegal_move_out_of_bounds(self) -> None:
        """Test that out of bounds move is rejected."""
        _game_engine, ui, _player1, _player2 = create_local_human_vs_human()

        ui.run()

        # Try out of bounds move - IndexError is raised directly
        with pytest.raises(IndexError, match="Move out of bounds"):
            ui.simulate_move(5, 5)

    def test_cannot_move_when_input_disabled(self) -> None:
        """Test that moves are rejected when input is disabled."""
        _game_engine, ui, _player1, _player2 = create_local_human_vs_human()

        ui.run()

        # Make a valid first move
        ui.simulate_move(0, 0)

        # Manually disable input to simulate waiting for other player
        ui._disable_input()

        # Try to move while input is disabled
        with pytest.raises(RuntimeError, match="Input is not enabled"):
            ui.simulate_move(1, 1)

    def test_cannot_move_when_not_current_player_turn(self) -> None:
        """Test that moves are rejected when it's not the current player's turn."""
        game_engine, ui, _player1, _player2 = create_local_human_vs_human()

        ui.run()

        # Player 1 (X) makes a move
        ui.simulate_move(0, 0)
        assert ui.get_board_state()[0][0] == "X"

        # Player 2 (O) makes a move
        ui.simulate_move(1, 0)
        assert ui.get_board_state()[1][0] == "O"

        # Apply a valid move for the player whose turn it is not
        available = game_engine.game.board.get_available_positions()
        assert len(available) > 0
        row, col = available[0]
        with pytest.raises(InvalidMoveError, match="Not your turn"):
            game_engine.game.apply_move(Move("O", row, col))

    def test_cannot_move_after_game_ends(self) -> None:
        """Test that no moves are allowed after the game has ended."""
        game_engine, ui, _player1, _player2 = create_local_human_vs_human()

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
        assert ui.game_finished
        assert ui.end_message is not None
        assert "Winner: X" in ui.end_message

        # Try to apply a move after game has ended
        available = game_engine.game.board.get_available_positions()
        assert len(available) > 0
        row, col = available[0]
        with pytest.raises(InvalidMoveError, match="Game over"):
            game_engine.game.apply_move(Move("O", row, col))


# ============================================================================
# ERROR HANDLING TESTS - Network Games
# ============================================================================


class TestNetworkHumanVsHumanErrorHandling:
    """Test error handling in network-based human vs human game."""

    def test_client_cannot_move_before_host_turn(self) -> None:
        (
            _game_engine_host,
            _game_engine_client,
            ui_host,
            ui_client,
            transport_host,
            transport_client,
        ) = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()

            with pytest.raises(RuntimeError, match="Input is not enabled"):
                ui_client.simulate_move(0, 0)

            assert ui_host.get_board_state()[0][0] is None
            assert ui_client.get_board_state()[0][0] is None

            assert len(ui_host.input_errors) == 0
            assert len(ui_client.input_errors) == 0
        finally:
            close_transports(transport_host, transport_client)

    def test_host_cannot_move_when_not_turn(self) -> None:
        (
            _game_engine_host,
            _game_engine_client,
            ui_host,
            ui_client,
            transport_host,
            transport_client,
        ) = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            ui_host.simulate_move(0, 0)
            wait_for_board_updates(ui_host, ui_client, 2, 2)

            with pytest.raises(RuntimeError, match="Input is not enabled"):
                ui_host.simulate_move(0, 1)

            assert ui_host.get_board_state()[0][1] is None
            assert ui_client.get_board_state()[0][1] is None

            assert len(ui_host.input_errors) == 0
            assert len(ui_client.input_errors) == 0
        finally:
            close_transports(transport_host, transport_client)

    def test_client_move_after_host_disconnect(self) -> None:
        (
            _game_engine_host,
            _game_engine_client,
            ui_host,
            ui_client,
            transport_host,
            transport_client,
        ) = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            ui_host.simulate_move(0, 0)
            wait_for_board_updates(ui_host, ui_client, 2, 2)

            transport_host._close()

            ui_client.simulate_move(1, 0)

            assert ui_client.get_board_state()[1][0] == "O"
            assert ui_host.get_board_state()[1][0] is None
        finally:
            close_transports(transport_host, transport_client)

    def test_host_move_after_client_disconnect(self) -> None:
        (
            _game_engine_host,
            _game_engine_client,
            ui_host,
            ui_client,
            transport_host,
            transport_client,
        ) = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            ui_host.simulate_move(0, 0)
            wait_for_board_updates(ui_host, ui_client, 2, 2)

            ui_client.simulate_move(1, 0)
            wait_for_board_updates(ui_host, ui_client, 3, 3)

            transport_client._close()

            ui_host.simulate_move(1, 1)

            assert ui_host.get_board_state()[1][1] == "X"
            assert ui_client.get_board_state()[1][1] is None
        finally:
            close_transports(transport_host, transport_client)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
