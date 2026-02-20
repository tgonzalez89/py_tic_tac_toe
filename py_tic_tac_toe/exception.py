class GameError(Exception):
    pass


class LogicError(GameError):
    pass


class InvalidMoveError(GameError):
    pass


class NetworkError(GameError):
    pass
