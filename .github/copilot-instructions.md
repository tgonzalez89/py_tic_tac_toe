# Copilot Instructions for py_tic_tac_toe

## Project Overview
A multiplayer Tic Tac Toe game engine with pluggable UI and player backends. Supports local play (human vs human, human vs AI), network play (TCP), and multiple concurrent UIs (terminal, pygame, tkinter).

## Architecture

### Event-Driven Core
The project uses a **publish-subscribe event bus** for all inter-component communication. This decouples components and enables multiple UI/player implementations to coexist.

- **EventBus** ([event_bus/event_bus.py](event_bus/event_bus.py)): Central pub-sub hub managing all events
- Key events: `StateUpdated`, `MoveRequested`, `StartTurn`, `EnableInput`, `InvalidMove`
- All components subscribe to relevant events; GameEngine publishes game state changes

### Component Layers

1. **Game Logic** ([game/game.py](game/game.py))
   - `TicTacToe`: Pure game rules (move validation, winner detection, turn management)
   - `Move`: Dataclass representing a player action
   - No external dependencies; fully testable in isolation

2. **Game Engine** ([game_engine/game_engine.py](game_engine/game_engine.py))
   - Orchestrates `TicTacToe` with event bus
   - Listens for `MoveRequested` events, applies moves, publishes `StateUpdated`
   - Entry point: `start()` initiates the game loop

3. **Players** ([player/](player/))
   - **Player (ABC)**: Base class subscribing to `StartTurn` event
   - **LocalPlayer**: Human input via UI
   - **RandomAIPlayer**: Random move selection
   - **LocalNetworkPlayer/RemoteNetworkPlayer**: Network-enabled variants
   - Players publish `MoveRequested` when ready to move

4. **UIs** ([ui/](ui/))
   - **Ui (ABC)**: Base class subscribing to `StateUpdated`, `InvalidMove`, `EnableInput`
   - **TerminalUi**, **PygameUi**, **TkUi**: Concrete implementations
   - Run in daemon threads; each instance manages its own input/output loop
   - Multiple UIs can run simultaneously, all viewing the same game

5. **Network** ([network/tcp_transport.py](network/tcp_transport.py))
   - **TcpTransport**: Low-level TCP messaging (JSON over sockets)
   - Runs receive loop in daemon thread
   - Provides blocking `recv()` and async `send()`; handlers for specific message types

### Initialization Flow ([__main__.py](__main__.py))
1. Parse arguments (mode: local/network, players, UIs, network config)
2. Create EventBus
3. Instantiate all UIs (start in daemon threads)
4. Configure players based on mode (LocalPlayer, AIPlayer, or NetworkPlayer variants)
5. Create GameEngine, subscribe to event bus
6. Call `engine.start()` to begin game

## Development Patterns

### Adding a New UI
1. Create class extending `Ui` abstract base
2. Implement: `start()`, `_on_state_updated()`, `_on_error()`, `_enable_input()`
3. Call `self.event_bus.publish(MoveRequested(...))` when user makes move
4. Register in [__main__.py](__main__.py) ui_choices dict

### Adding a New Player Type
1. Create class extending `Player` abstract base
2. Implement `_on_start_turn()` callback (called via event bus when turn begins)
3. Publish `MoveRequested` event when ready to move
4. Add instantiation logic in [__main__.py](__main__.py)

### Event Flow Pattern
```
User Input → UI publishes MoveRequested
           → GameEngine catches MoveRequested
           → GameEngine applies move to TicTacToe
           → GameEngine publishes StateUpdated
           → All UIs and Players receive StateUpdated
           → Next player's StartTurn triggers (via GameEngine)
           → Player responds with MoveRequested (cycle repeats)
```

## Code Standards

- **Type hints required**: `mypy --strict` configuration enforced
- **Code style**: Ruff with ALL rules selected (line length: 120)
- **Python version**: 3.13+
- **Imports**: Type-checking conditional imports used to avoid circular dependencies ([__main__.py](__main__.py) line 5)
- **Dataclasses**: Frozen dataclasses for immutable event objects
- **Threads**: Daemon threads for UI and network loops; main thread blocks on startup

## Testing & Running

**Entry point**: `python -m py_tic_tac_toe --mode {local|network} --player-x {human|ai} --player-o {human|ai} --ui {terminal|pygame|tk} [--host HOST] [--port PORT]`

**Examples**:
- Local human vs AI: `--mode local --player-x human --player-o ai --ui terminal`
- Network: `--mode network --role host --ui pygame` + `--role client` on another process

## Key Files for Common Tasks

- **Add game rule**: [game/game.py](game/game.py) - modify `TicTacToe` class
- **Fix game logic bug**: [game_engine/game_engine.py](game_engine/game_engine.py) - debug event handling
- **UI input handling**: [ui/ui.py](ui/ui.py) - implement in concrete UI subclass
- **Player behavior**: [player/player.py](player/player.py) - modify concrete player class
- **Network issues**: [network/tcp_transport.py](network/tcp_transport.py) - check message serialization
- **Event system**: [event_bus/event_bus.py](event_bus/event_bus.py) - add new event types or debug pub-sub

## Critical Integration Points

1. **EventBus is a singleton passed to all components** - No global state; all dependencies injected
2. **Moves validated at game logic layer** - GameEngine catches exceptions from `TicTacToe.apply_move()`, publishes `InvalidMove`
3. **Network players bridge via TcpTransport** - Messages contain move coordinates; no complex serialization needed
4. **UI threads are non-blocking** - Main thread waits on `ui.start()` calls; UIs handle their own event loops internally
