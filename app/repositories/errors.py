from __future__ import annotations


class RepositoryError(RuntimeError):
    """Base error for persistence boundary failures."""


class NotFoundError(RepositoryError):
    """Raised when a requested persisted object does not exist."""


class PermissionDeniedError(RepositoryError):
    """Raised when an authenticated principal is not eligible for an operation."""


class ConflictError(RepositoryError):
    """Raised when persisted state conflicts with the requested operation."""


class PersistenceError(RepositoryError):
    """Raised when the underlying backend cannot complete the operation."""


class PurchaseRejectedError(RepositoryError):
    """A whitelisted business rejection, never a raw database exception."""

    def __init__(self, code: str, status: int):
        super().__init__(code)
        self.code = code
        self.status = status


class RedemptionRejectedError(RepositoryError):
    """Whitelisted redemption rejection, safe to expose without SQL details."""

    def __init__(self, code: str, status: int):
        super().__init__(code)
        self.code, self.status = code, status
