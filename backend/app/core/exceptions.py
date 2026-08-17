class AppError(Exception):
    """Base class for domain errors raised from the service layer.

    Kept independent of FastAPI so services stay framework-agnostic; the API
    layer translates these into HTTPExceptions.
    """


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class ValidationError(AppError):
    pass


class AuthError(AppError):
    pass
