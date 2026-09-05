"""
Domain-level exceptions.

Design decision: services raise these plain Python exceptions, NOT
FastAPI's HTTPException. This keeps the service layer framework-agnostic
(it could be reused behind a CLI, a worker queue, gRPC, etc.) — the API
layer is responsible for catching these and translating them into the
appropriate HTTP status codes.
"""


class DomainError(Exception):
    """Base class for all domain/service-layer errors."""


class DuplicateEmailError(DomainError):
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"An account with email '{email}' already exists")


class InvalidCredentialsError(DomainError):
    def __init__(self):
        super().__init__("Incorrect email or password")


class InactiveUserError(DomainError):
    def __init__(self):
        super().__init__("This account has been deactivated")


class InvalidTokenError(DomainError):
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(detail)


class InsufficientPermissionsError(DomainError):
    def __init__(self):
        super().__init__("You do not have permission to perform this action")


class NotFoundError(DomainError):
    def __init__(self, entity: str, identifier: str):
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} with id '{identifier}' was not found")


class InsufficientDataError(DomainError):
    def __init__(self, detail: str):
        super().__init__(detail)


class AssistantUnavailableError(DomainError):
    """Raised when the AI Health Assistant's LLM backend isn't configured
    (no API key set) or the call to it failed. Distinct from other
    DomainErrors so the API layer can map it to 503 rather than 400/404 —
    this is a service configuration/availability issue, not something the
    caller's request got wrong."""

    def __init__(self, detail: str = "The AI Health Assistant is currently unavailable"):
        super().__init__(detail)
