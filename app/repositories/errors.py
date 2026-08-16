from __future__ import annotations


class RepositoryError(RuntimeError):
    """Base error for persistence boundary failures."""


class NotFoundError(RepositoryError):
    """Raised when a requested persisted object does not exist."""


class ConflictError(RepositoryError):
    """Raised when persisted state conflicts with the requested operation."""


class PersistenceError(RepositoryError):
    """Raised when the underlying backend cannot complete the operation."""
