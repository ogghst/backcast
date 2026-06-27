"""custom_fields_phase0

Revision ID: c93e9767de59
Revises: e00199978962
Create Date: 2026-06-27 00:00:00.000000

Phase 0 of the admin-defined Custom Fields initiative (see memory note 44 /
docs/03-project-plan/iterations/2026-06-24-custom-fields-analysis/).

Schema changes (no application logic yet — models, services, schemas ship in
later phases):

1. ``custom_fields`` JSONB dict + ``custom_entity_template_root_id`` UUID +
   ``custom_field_definitions_snapshot`` JSONB added (nullable, no server
   default) to the three branchable project-scope tables ``projects``,
   ``wbs_elements``, ``work_packages``.

2. ``change_orders`` already has a ``custom_field_values`` JSONB column (added
   with the change-order feature). It is renamed to ``custom_fields`` for
   consistency, then gains the same two template-link columns.

3. C1 — unique partial index per branchable table guaranteeing at most one
   current version per (root_id, branch):

       CREATE UNIQUE INDEX ix_<t>_current_version
       ON <t> (root_id, branch)
       WHERE upper(valid_time) IS NULL AND deleted_at IS NULL;

   This is the real concurrency control for the "current version" invariant
   (the v3 "optimistic lock" was a non-serializing TOCTOU and was withdrawn).
   It enforces one open-valid_time current version per (root, branch);
   ADR-005 additionally requires upper(transaction_time) IS NULL,
   intentionally deferred per frozen decision C1 (see functional-analysis §6.4).
   It closes M14/M15 of the adversarial review.

4. ``custom_entity_templates`` table — the Versionable (NOT branchable),
   org-scoped template registry backing the new ``CustomEntityTemplate`` model
   in app/models/domain/custom_entity_template.py. Mirrors CostElementType
   structurally (EntityBase + VersionableMixin). The C1 unique partial index
   ``ix_custom_entity_templates_current`` enforces exactly one current version
   per template root.

A dedup pre-step soft-deletes pre-existing duplicate current versions per
(root, branch) on each branchable table so the unique partial index can be
created. Safe no-op on a clean DB (dev DB has 0 such duplicates today, verified
2026-06-27). The lost-update race that could create such duplicates is exactly
what C1 now prevents at the DB layer. The downgrade does NOT undo the
soft-deletes — that data is gone — it only drops the index.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c93e9767de59"
down_revision: Union[str, Sequence[str], None] = "e00199978962"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# (root_id, table) pairs for the 4 branchable tables. Each entry drives the
# dedup pre-step (c), the C1 unique partial index (d), and the downgrade.
# ---------------------------------------------------------------------------
_BRANCHABLE_TABLES: list[tuple[str, str]] = [
    ("projects", "project_id"),
    ("wbs_elements", "wbs_element_id"),
    ("work_packages", "work_package_id"),
    ("change_orders", "change_order_id"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # -------------------------------------------------------------------------
    # (a) projects / wbs_elements / work_packages: add 3 nullable columns.
    #     No server_default — existing rows simply have NULL custom fields,
    #     which the application layer treats as "no custom fields defined".
    # -------------------------------------------------------------------------
    for table in ("projects", "wbs_elements", "work_packages"):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "custom_fields",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                )
            )
            batch_op.add_column(
                sa.Column("custom_entity_template_root_id", sa.UUID(), nullable=True)
            )
            batch_op.add_column(
                sa.Column(
                    "custom_field_definitions_snapshot",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                )
            )

    # -------------------------------------------------------------------------
    # (b) change_orders: rename custom_field_values -> custom_fields, then add
    #     the two template-link columns. The rename is the only deviation from
    #     (a) — change_orders pre-dates the initiative and already carried a
    #     JSONB values column.
    # -------------------------------------------------------------------------
    with op.batch_alter_table("change_orders", schema=None) as batch_op:
        batch_op.alter_column("custom_field_values", new_column_name="custom_fields")
        batch_op.add_column(
            sa.Column("custom_entity_template_root_id", sa.UUID(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "custom_field_definitions_snapshot",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            )
        )

    # -------------------------------------------------------------------------
    # (c) Dedup pre-step per branchable table.
    #
    # Clean up pre-existing duplicate current versions — the lost-update race
    # that C1 now prevents — so the unique partial index can be created. Safe
    # no-op on a clean DB (verified 0 duplicates on 2026-06-27 dev DB).
    #
    # Keeps the newest current version per (root, branch) — ranked by
    # transaction_time then valid_time lower bounds, both DESC — and
    # soft-deletes the rest via deleted_at = clock_timestamp().
    # -------------------------------------------------------------------------
    for table, root in _BRANCHABLE_TABLES:
        op.execute(
            sa.text(
                f"""
                UPDATE {table}
                SET deleted_at = clock_timestamp()
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY {root}, branch
                                   ORDER BY lower(transaction_time) DESC,
                                            lower(valid_time) DESC
                               ) AS rn
                        FROM {table}
                        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL
                    ) s
                    WHERE rn > 1
                )
                """
            )
        )

    # -------------------------------------------------------------------------
    # (d) C1 unique partial indexes on the 4 branchable tables.
    #
    # Exactly one current (open valid_time, non-deleted) version per
    # (root_id, branch). This is the real concurrency control for the current-
    # version invariant — DB-enforced, serialization-safe.
    # -------------------------------------------------------------------------
    for table, root in _BRANCHABLE_TABLES:
        op.create_index(
            f"ix_{table}_current_version",
            table,
            [root, "branch"],
            unique=True,
            postgresql_where=sa.text(
                "upper(valid_time) IS NULL AND deleted_at IS NULL"
            ),
        )

    # -------------------------------------------------------------------------
    # (e) custom_entity_templates table — mirrors the model in
    #     app/models/domain/custom_entity_template.py EXACTLY (EntityBase id PK,
    #     VersionableMixin temporal cols with the same server_default as
    #     mixins.py, the template's own root/org/target/code/name/description/
    #     field_definitions columns, plus the C1 unique partial index).
    # -------------------------------------------------------------------------
    op.create_table(
        "custom_entity_templates",
        # --- EntityBase ---
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # --- CustomEntityTemplate columns ---
        sa.Column(
            "custom_entity_template_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "organizational_unit_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("target_entity_type", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "field_definitions", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        # --- VersionableMixin (server_default mirrors mixins.py:29-39) ---
        sa.Column(
            "valid_time",
            postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), NULL, '[]')"),
            nullable=False,
        ),
        sa.Column(
            "transaction_time",
            postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), NULL, '[]')"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Plain btree indexes mirroring the model's index=True columns.
    op.create_index(
        op.f("ix_custom_entity_templates_custom_entity_template_id"),
        "custom_entity_templates",
        ["custom_entity_template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_custom_entity_templates_organizational_unit_id"),
        "custom_entity_templates",
        ["organizational_unit_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_custom_entity_templates_target_entity_type"),
        "custom_entity_templates",
        ["target_entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_custom_entity_templates_code"),
        "custom_entity_templates",
        ["code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_custom_entity_templates_created_by"),
        "custom_entity_templates",
        ["created_by"],
        unique=False,
    )

    # C1 unique partial index — exactly one current version per template root.
    op.create_index(
        "ix_custom_entity_templates_current",
        "custom_entity_templates",
        ["custom_entity_template_id"],
        unique=True,
        postgresql_where=sa.text("upper(valid_time) IS NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema (reverse of upgrade, EXCEPT the dedup soft-deletes —
    that data is unrecoverable; only the indexes are dropped)."""
    # -------------------------------------------------------------------------
    # (e) reverse: drop custom_entity_templates indexes + table.
    # -------------------------------------------------------------------------
    op.drop_index(
        "ix_custom_entity_templates_current",
        table_name="custom_entity_templates",
        postgresql_where=sa.text("upper(valid_time) IS NULL AND deleted_at IS NULL"),
    )
    op.drop_index(
        op.f("ix_custom_entity_templates_created_by"),
        table_name="custom_entity_templates",
    )
    op.drop_index(
        op.f("ix_custom_entity_templates_code"),
        table_name="custom_entity_templates",
    )
    op.drop_index(
        op.f("ix_custom_entity_templates_target_entity_type"),
        table_name="custom_entity_templates",
    )
    op.drop_index(
        op.f("ix_custom_entity_templates_organizational_unit_id"),
        table_name="custom_entity_templates",
    )
    op.drop_index(
        op.f("ix_custom_entity_templates_custom_entity_template_id"),
        table_name="custom_entity_templates",
    )
    op.drop_table("custom_entity_templates")

    # -------------------------------------------------------------------------
    # (d) reverse: drop the 4 C1 unique partial indexes. drop_index MUST
    #     repeat the same postgresql_where as the create_index.
    # -------------------------------------------------------------------------
    for table, _root in _BRANCHABLE_TABLES:
        op.drop_index(
            f"ix_{table}_current_version",
            table_name=table,
            postgresql_where=sa.text(
                "upper(valid_time) IS NULL AND deleted_at IS NULL"
            ),
        )

    # -------------------------------------------------------------------------
    # (b) reverse: change_orders — drop the two added columns, then rename
    #     custom_fields -> custom_field_values (restoring the pre-initiative
    #     name). NOTE: only safe if the column still holds raw values and was
    #     not repopulated with the new init shape — which Phase 0 guarantees.
    # -------------------------------------------------------------------------
    with op.batch_alter_table("change_orders", schema=None) as batch_op:
        batch_op.drop_column("custom_field_definitions_snapshot")
        batch_op.drop_column("custom_entity_template_root_id")
        batch_op.alter_column("custom_fields", new_column_name="custom_field_values")

    # -------------------------------------------------------------------------
    # (a) reverse: projects / wbs_elements / work_packages — drop 3 columns.
    # -------------------------------------------------------------------------
    for table in ("projects", "wbs_elements", "work_packages"):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("custom_field_definitions_snapshot")
            batch_op.drop_column("custom_entity_template_root_id")
            batch_op.drop_column("custom_fields")
