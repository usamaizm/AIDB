"""Stable machine-readable errors for AIDB's public APIs."""

from __future__ import annotations

import sqlite3
from typing import Any


class AIDBError(ValueError):
    code = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidArgumentError(AIDBError):
    code = "invalid_argument"


class NotFoundError(AIDBError):
    code = "not_found"


class AlreadyExistsError(AIDBError):
    code = "already_exists"


class RevisionConflictError(AIDBError):
    code = "revision_conflict"


class IntegrityFailureError(AIDBError):
    code = "integrity_failure"


class UnsupportedVersionError(AIDBError):
    code = "unsupported_version"


class UnsupportedCapabilityError(AIDBError):
    code = "unsupported_capability"


class UnauthenticatedError(AIDBError):
    code = "unauthenticated"


class TemporarilyUnavailableError(AIDBError):
    code = "temporarily_unavailable"


class InternalError(AIDBError):
    code = "internal_error"


class StorageIntegrityError(sqlite3.IntegrityError, AIDBError):
    """Storage constraint failure with a stable code and SQLite compatibility."""

    code = "integrity_failure"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        sqlite3.IntegrityError.__init__(self, message)
        self.message = message
        self.details = details or {}


class PermissionDeniedError(PermissionError, AIDBError):
    code = "permission_denied"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        PermissionError.__init__(self, message)
        self.message = message
        self.details = details or {}


__all__ = [
    "AIDBError",
    "AlreadyExistsError",
    "IntegrityFailureError",
    "InvalidArgumentError",
    "NotFoundError",
    "PermissionDeniedError",
    "RevisionConflictError",
    "UnsupportedVersionError",
    "UnsupportedCapabilityError",
    "UnauthenticatedError",
    "TemporarilyUnavailableError",
    "InternalError",
    "StorageIntegrityError",
]
