from abc import ABC, abstractmethod

from py_tic_tac_toe.event_bus.event_bus import EnableInput, EventBus, InputError, StateUpdated


class Ui(ABC):
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._event_bus.subscribe(StateUpdated, self._on_state_updated)
        self._event_bus.subscribe(InputError, self._on_input_error)
        self._event_bus.subscribe(EnableInput, self._enable_input)
        self._started = False

    @abstractmethod
    def start(self) -> None:  # noqa: D102
        pass

    @abstractmethod
    def stop(self) -> None:  # noqa: D102
        pass

    @property
    def started(self) -> bool:  # noqa: D102
        return self._started

    @abstractmethod
    def _enable_input(self, player: EnableInput) -> None:
        pass

    @abstractmethod
    def _on_state_updated(self, event: StateUpdated) -> None:
        pass

    @abstractmethod
    def _on_input_error(self, event: InputError) -> None:
        pass
