import socket
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from py_tic_tac_toe.board import Move, PlayerSymbol
from py_tic_tac_toe.exception import InvalidMoveError, NetworkError
from py_tic_tac_toe.factories import _create_network_player, config_game_engine, create_local_players
from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.player_ai import HardAiPlayer, RandomAiPlayer
from py_tic_tac_toe.player_local import LocalPlayer
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

    def _on_input_error(self, exception: Exception) -> None:
        """Track input errors."""
        self.input_errors.append(exception)

    def _on_other_error(self, exception: Exception) -> None:
        """Track other errors (network, etc)."""
        self.input_errors.append(exception)

    def get_board_state(self) -> list[list[PlayerSymbol | None]]:
        """Get current board state."""
        return self._game_engine.game.board.board

    def simulate_move(self, row: int, col: int) -> None:
        """Simulate a user input move (for local players)."""
        if not self._input_enabled:
            raise RuntimeError("Input is not enabled - cannot move now")
        self._queue_move(row, col)
        self._game_engine.tick()


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def create_local_human_vs_human() -> tuple[GameEngine, FakeUI]:
    game_engine = GameEngine()
    ui = FakeUI(game_engine)

    player1, player2 = create_local_players("human", "human", game_engine.game.board, [ui])
    config_game_engine(game_engine, (player1, player2), [ui])

    return game_engine, ui


def create_network_human_vs_human() -> tuple[FakeUI, FakeUI, TcpTransport, TcpTransport]:
    game_engine_host = GameEngine()
    game_engine_client = GameEngine()

    ui_host = FakeUI(game_engine_host)
    ui_client = FakeUI(game_engine_client)

    port = get_free_port()

    # Create transports first (they block each other, so use ThreadPool)
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_host = executor.submit(create_host_transport, port)
        future_client = executor.submit(create_client_transport, "127.0.0.1", port)
        transport_host: TcpTransport = future_host.result()
        transport_client: TcpTransport = future_client.result()

    # Create host players first (non-blocking, just send symbol assignment messages)
    player1_host = _create_network_player("local", [ui_host], transport_host, game_engine_host.game.board, "X")
    player2_host = _create_network_player("remote", [ui_host], transport_host, game_engine_host.game.board, "O")

    # Create client players (may block briefly waiting for host symbols, but host is ready)
    player1_client = _create_network_player("remote", [ui_client], transport_client, game_engine_client.game.board)
    player2_client = _create_network_player("local", [ui_client], transport_client, game_engine_client.game.board)

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
        ui_host._game_engine.tick()
        ui_client._game_engine.tick()
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
        _game_engine, ui = create_local_human_vs_human()

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

        player1 = LocalPlayer("X")
        player2 = RandomAiPlayer("O", game_engine.game.board)

        player1.add_enable_input_cb(ui.enable_input)

        game_engine.set_players(player1, player2)
        game_engine.add_board_updated_cb(ui.on_board_updated)

        ui.run()

        # Simulate game by manually playing moves
        # Human plays X
        ui.simulate_move(0, 0)
        game_engine.tick()  # Advance game to let AI make its move

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
                game_engine.tick()  # Advance game to let AI make its move

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

        player1 = RandomAiPlayer("X", game_engine.game.board)
        player2 = LocalPlayer("O")

        player2.add_enable_input_cb(ui.enable_input)

        game_engine.set_players(player1, player2)
        game_engine.add_board_updated_cb(ui.on_board_updated)

        ui.run()
        game_engine.tick()  # Advance game to let AI make its move

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
        game_engine.tick()  # Advance game to let AI make its move
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
                game_engine.tick()  # Advance game to let AI make its move

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

        player1 = RandomAiPlayer("X", game_engine.game.board)
        player2 = RandomAiPlayer("O", game_engine.game.board)

        game_engine.set_players(player1, player2)
        game_engine.add_board_updated_cb(ui.on_board_updated)

        ui.run()

        # AI vs AI game completes automatically through game loop
        # Just wait for it to finish or timeout
        timeout = time.time() + 5
        while not ui.game_finished and time.time() < timeout:
            game_engine.tick()  # Advance game to let AI make its move

        assert ui.game_finished
        assert ui.end_message is not None
        assert "Winner:" in ui.end_message or "draw" in ui.end_message
        assert len(ui.input_errors) == 0

    def test_hard_ai_vs_hard_ai(self) -> None:
        """Test hard AI vs hard AI game - should always result in a draw."""
        game_engine = GameEngine()
        ui = FakeUI(game_engine)

        player1 = HardAiPlayer("X", game_engine.game.board)
        player2 = HardAiPlayer("O", game_engine.game.board)

        game_engine.set_players(player1, player2)
        game_engine.add_board_updated_cb(ui.on_board_updated)

        ui.run()

        # AI vs AI game completes automatically through game loop
        # Just wait for it to finish or timeout
        timeout = time.time() + 5
        while not ui.game_finished and time.time() < timeout:
            game_engine.tick()  # Advance game to let AI make its move

        assert ui.game_finished
        assert ui.end_message is not None
        # Hard AI vs Hard AI should always end in a draw (both play optimally)
        assert "draw" in ui.end_message
        assert len(ui.input_errors) == 0


# ============================================================================
# HAPPY PATH TESTS - Network Games
# ============================================================================


class TestNetworkHumanVsHuman:
    """Test network-based human vs human game."""

    def test_network_human_vs_human_complete_game(self) -> None:
        """Test a complete network human vs human game."""
        ui_host, ui_client, transport_host, transport_client = create_network_human_vs_human()

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
        _game_engine, ui = create_local_human_vs_human()

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
        _game_engine, ui = create_local_human_vs_human()

        ui.run()

        # Try out of bounds move - IndexError is raised directly
        with pytest.raises(IndexError, match="Move out of bounds"):
            ui.simulate_move(5, 5)

    def test_cannot_move_when_input_disabled(self) -> None:
        """Test that moves are rejected when input is disabled."""
        _game_engine, ui = create_local_human_vs_human()

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
        game_engine, ui = create_local_human_vs_human()

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
        ui_host, ui_client, transport_host, transport_client = create_network_human_vs_human()

        try:
            ui_host.run()
            ui_client.run()
            wait_for_board_updates(ui_host, ui_client, 1, 1)

            with pytest.raises(RuntimeError, match="Input is not enabled"):
                ui_client.simulate_move(0, 0)

            assert ui_host.get_board_state()[0][0] is None
            assert ui_client.get_board_state()[0][0] is None

            assert len(ui_host.input_errors) == 0
            assert len(ui_client.input_errors) == 0
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

            assert ui_host.get_board_state()[0][1] is None
            assert ui_client.get_board_state()[0][1] is None

            assert len(ui_host.input_errors) == 0
            assert len(ui_client.input_errors) == 0
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

            ui_client.simulate_move(1, 0)

            # Move should fail with network error
            assert len(ui_client.input_errors) == 1

            assert isinstance(ui_client.input_errors[0], NetworkError)
            # Move should not be applied
            assert ui_client.get_board_state()[1][0] is None
            assert ui_host.get_board_state()[1][0] is None
        finally:
            close_transports(transport_host, transport_client)

    def test_host_move_after_client_disconnect(self) -> None:
        ui_host, ui_client, transport_host, transport_client = create_network_human_vs_human()

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

            # Move should fail with network error
            assert len(ui_host.input_errors) == 1

            assert isinstance(ui_host.input_errors[0], NetworkError)
            # Move should not be applied
            assert ui_host.get_board_state()[1][1] is None
            assert ui_client.get_board_state()[1][1] is None
        finally:
            close_transports(transport_host, transport_client)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
