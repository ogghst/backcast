"""Shared helpers for translating database errors into HTTP responses."""

from sqlalchemy.exc import IntegrityError

# PostgreSQL SQLSTATE for unique_violation.
UNIQUE_VIOLATION_SQLSTATE = "23505"


def is_unique_violation(exc: IntegrityError) -> bool:
    """True if the IntegrityError is a PostgreSQL unique-violation.

    Checks the underlying DBAPI exception's ``sqlstate`` attribute, which
    asyncpg exposes on ``PostgresError`` (surfaced by SQLAlchemy as
    ``IntegrityError.orig``).
    """
    orig = getattr(exc, "orig", None)
    return getattr(orig, "sqlstate", None) == UNIQUE_VIOLATION_SQLSTATE
