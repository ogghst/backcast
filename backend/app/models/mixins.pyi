"""Type stubs for mixins module.

These stub files help MyPy understand the types of SQLAlchemy ORM classes
that use complex metaclass programming.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import TSTZRANGE as PG_TSTZRANGE
from sqlalchemy.orm import Mapped

class VersionableMixin:
    """Mixin for temporal versioning - compose with EntityBase."""

    valid_time: Mapped[PG_TSTZRANGE]
    transaction_time: Mapped[PG_TSTZRANGE]
    deleted_at: Mapped[datetime | None]
    created_by: Mapped[UUID]
    deleted_by: Mapped[UUID | None]

    @property
    def is_deleted(self) -> bool: ...

    def soft_delete(self) -> None: ...

    def undelete(self) -> None: ...

    def clone(self, **overrides: Any) -> VersionableMixin: ...

class BranchableMixin:
    """Mixin for branching - compose with VersionableMixin."""

    branch: Mapped[str]
    parent_id: Mapped[UUID | None]
    merge_from_branch: Mapped[str | None]

    @property
    def is_current(self) -> bool: ...
