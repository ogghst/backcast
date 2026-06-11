"""Baseline schema — represents the full database as of 2026-06-02.

This is a squashed migration that replaces 108 fragmented/broken migration
files. The database was managed via reseed (Base.metadata.create_all), not
Alembic, so no incremental history is needed.

For fresh databases: use `reseed` or `alembic upgrade head`.
For existing databases: `alembic stamp head` (schema already exists).

Revision ID: 0001_baseline
Revises: None
Create Date: 2026-06-02
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import MetaData

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create full schema from SQLAlchemy models.

    Uses metadata.create_all to generate all tables, indexes, and constraints
    from the current model definitions. Safe to run on an existing database
    (create_all skips tables that already exist).
    """
    # Import Base and all models to register them in the metadata
    from app.core.base.base import Base  # noqa: F401
    import app.models.domain.ai  # noqa: F401
    import app.models.domain.branch  # noqa: F401
    import app.models.domain.change_order  # noqa: F401
    import app.models.domain.change_order_audit_log  # noqa: F401
    import app.models.domain.change_order_config  # noqa: F401
    import app.models.domain.control_account  # noqa: F401
    import app.models.domain.cost_element  # noqa: F401
    import app.models.domain.cost_element_type  # noqa: F401
    import app.models.domain.cost_event  # noqa: F401
    import app.models.domain.cost_event_type  # noqa: F401
    import app.models.domain.cost_registration  # noqa: F401
    import app.models.domain.cost_registration_attachment  # noqa: F401
    import app.models.domain.dashboard_layout  # noqa: F401
    import app.models.domain.document  # noqa: F401
    import app.models.domain.document_entity_link  # noqa: F401
    import app.models.domain.document_folder  # noqa: F401
    import app.models.domain.document_version  # noqa: F401
    import app.models.domain.forecast  # noqa: F401
    import app.models.domain.mcp_server  # noqa: F401
    import app.models.domain.notification  # noqa: F401
    import app.models.domain.organizational_unit  # noqa: F401
    import app.models.domain.progress_entry  # noqa: F401
    import app.models.domain.project  # noqa: F401
    import app.models.domain.project_budget_settings  # noqa: F401
    import app.models.domain.rbac  # noqa: F401
    import app.models.domain.refresh_token  # noqa: F401
    import app.models.domain.schedule_baseline  # noqa: F401
    import app.models.domain.user  # noqa: F401
    import app.models.domain.user_role_assignment  # noqa: F401
    import app.models.domain.wbs_element  # noqa: F401
    import app.models.domain.work_package  # noqa: F401

    connection = op.get_bind()
    Base.metadata.create_all(connection)


def downgrade() -> None:
    """Drop all tables.

    WARNING: This destroys all data. Typically only used in development.
    """
    from app.core.base.base import Base  # noqa: F401
    import app.models.domain.ai  # noqa: F401
    import app.models.domain.branch  # noqa: F401
    import app.models.domain.change_order  # noqa: F401
    import app.models.domain.change_order_audit_log  # noqa: F401
    import app.models.domain.change_order_config  # noqa: F401
    import app.models.domain.control_account  # noqa: F401
    import app.models.domain.cost_element  # noqa: F401
    import app.models.domain.cost_element_type  # noqa: F401
    import app.models.domain.cost_event  # noqa: F401
    import app.models.domain.cost_event_type  # noqa: F401
    import app.models.domain.cost_registration  # noqa: F401
    import app.models.domain.cost_registration_attachment  # noqa: F401
    import app.models.domain.dashboard_layout  # noqa: F401
    import app.models.domain.document  # noqa: F401
    import app.models.domain.document_entity_link  # noqa: F401
    import app.models.domain.document_folder  # noqa: F401
    import app.models.domain.document_version  # noqa: F401
    import app.models.domain.forecast  # noqa: F401
    import app.models.domain.mcp_server  # noqa: F401
    import app.models.domain.notification  # noqa: F401
    import app.models.domain.organizational_unit  # noqa: F401
    import app.models.domain.progress_entry  # noqa: F401
    import app.models.domain.project  # noqa: F401
    import app.models.domain.project_budget_settings  # noqa: F401
    import app.models.domain.rbac  # noqa: F401
    import app.models.domain.refresh_token  # noqa: F401
    import app.models.domain.schedule_baseline  # noqa: F401
    import app.models.domain.user  # noqa: F401
    import app.models.domain.user_role_assignment  # noqa: F401
    import app.models.domain.wbs_element  # noqa: F401
    import app.models.domain.work_package  # noqa: F401

    connection = op.get_bind()
    # Drop all tables registered in metadata (reverse dependency order)
    Base.metadata.drop_all(connection)
