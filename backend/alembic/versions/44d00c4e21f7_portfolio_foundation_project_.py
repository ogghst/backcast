"""portfolio foundation: project attribution + customer

Revision ID: 44d00c4e21f7
Revises: c93e9767de59
Create Date: 2026-06-28 16:16:24.003979

Portfolio foundation (Part 1, steps 5+6):

- New ``customers`` table (non-versioned SimpleEntityBase: code/name/desc/active).
- New ``currency_rates`` table (non-versioned FX reference ledger).
- Three nullable root-id attribution columns on ``projects``:
  organizational_unit_id, project_manager_id, customer_id (indexed, no DB FK —
  integrity is app-level per the EVCS root-id convention).
- Idempotent seed of the GLOBAL organizational unit (root id
  00000000-0000-4000-8000-00000000fffd — a DISTINCT id reserved for the
  portfolio root, deliberately NOT colliding with the seed_projects.json
  Engineering unit at ...0001) when absent.
- Idempotent seed of EUR->1.0 base rate effective CURRENT_DATE.
- Backfill: current-version main-branch projects get project_manager_id =
  created_by and organizational_unit_id = GLOBAL root id (customer_id stays
  NULL).

NOTE: autogenerate also reported unrelated drift on schedule_dependencies /
ai_agent_schedules partial index — that is pre-existing DB/metadata drift and
is intentionally NOT touched here (surgical scope).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "44d00c4e21f7"
down_revision: Union[str, Sequence[str], None] = "c93e9767de59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Root id of the GLOBAL organizational unit (also referenced as
# GLOBAL_ORG_UNIT_ID in app/db/seed_custom_templates.py). Seeding here ensures a
# fresh install has a global OU before the reseed runs. Deliberately DISTINCT
# from the seed_projects.json Engineering unit (...0001) — using ...0001 here
# made the NOT-EXISTS guard a no-op on dev DBs (ENG already populated it) and
# the backfill then attributed everything to Engineering instead of the global
# root. ...fffd is reserved exclusively for the portfolio GLOBAL root.
GLOBAL_ORG_UNIT_ROOT_ID = "00000000-0000-4000-8000-00000000fffd"
# Sentinel PK for the GLOBAL OU seed row (idempotent: guarded by NOT EXISTS on
# the root id, so a fixed PK is safe).
GLOBAL_ORG_UNIT_PK = "00000000-0000-4000-8000-00000000fffd"
SYSTEM_ACTOR = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    """Upgrade schema + idempotent seeds + backfill."""
    # --- customers ---
    op.create_table(
        "customers",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_customers_code"), ["code"], unique=False
        )
        # Active codes are unique (soft-deleted rows may reuse a code).
        batch_op.create_index(
            "uq_customers_code_active",
            ["code"],
            unique=True,
            postgresql_where=sa.text("is_active"),
        )

    # --- currency_rates ---
    op.create_table(
        "currency_rates",
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "rate_to_base", sa.Numeric(precision=15, scale=6), nullable=False
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("currency_rates", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_currency_rates_currency"),
            ["currency"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_currency_rates_effective_date"),
            ["effective_date"],
            unique=False,
        )

    # --- projects attribution columns (root-id FKs, no DB constraint) ---
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("organizational_unit_id", sa.UUID(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("project_manager_id", sa.UUID(), nullable=True)
        )
        batch_op.add_column(sa.Column("customer_id", sa.UUID(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_projects_customer_id"), ["customer_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_projects_organizational_unit_id"),
            ["organizational_unit_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_projects_project_manager_id"),
            ["project_manager_id"],
            unique=False,
        )

    # --- Idempotent seed: GLOBAL organizational unit ---
    # Mirrors the EVCS row shape (valid_time/transaction_time open-ended
    # tstzrange, branch='main', created_by=SYSTEM_ACTOR). Guarded by NOT EXISTS
    # on the DISTINCT GLOBAL root id (...fffd), so re-runs / reseeds are no-ops
    # and the row never collides with the seed_projects.json Engineering unit
    # (...0001). UUID literals are cast ::uuid inline because asyncpg binds text
    # params and the columns are uuid-typed (operator uuid = varchar would
    # otherwise fail).
    op.execute(
        sa.text(
            f"""
            INSERT INTO organizational_units
                (id, organizational_unit_id, parent_unit_id, code, name,
                 manager_id, is_active, description,
                 valid_time, transaction_time, deleted_at, created_by,
                 branch, parent_id, merge_from_branch)
            SELECT
                '{GLOBAL_ORG_UNIT_PK}'::uuid, '{GLOBAL_ORG_UNIT_ROOT_ID}'::uuid,
                NULL, 'GLOBAL', 'Global',
                NULL, TRUE, 'Global organizational unit (portfolio root)',
                tstzrange(NOW(), NULL), tstzrange(NOW(), NULL), NULL,
                '{SYSTEM_ACTOR}'::uuid,
                'main', NULL, NULL
            WHERE NOT EXISTS (
                SELECT 1 FROM organizational_units
                WHERE organizational_unit_id = '{GLOBAL_ORG_UNIT_ROOT_ID}'::uuid
            )
            """
        )
    )

    # --- Idempotent seed: EUR -> 1.0 base rate effective today ---
    op.execute(
        sa.text(
            """
            INSERT INTO currency_rates
                (id, currency, rate_to_base, effective_date, created_at, updated_at)
            SELECT
                gen_random_uuid(), 'EUR', 1.0, CURRENT_DATE, NOW(), NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM currency_rates
                WHERE currency = 'EUR' AND effective_date = CURRENT_DATE
            )
            """
        )
    )

    # --- Backfill: current-version main-branch projects get attribution defaults ---
    # project_manager_id <- created_by (best available proxy for ownership).
    # organizational_unit_id <- GLOBAL root. customer_id stays NULL (unknown).
    # Restricted to branch='main' + current-version rows (open valid_time,
    # non-deleted) to mirror the standalone sync_seed_project_attribution.py tool.
    op.execute(
        sa.text(
            f"""
            UPDATE projects
            SET project_manager_id = created_by,
                organizational_unit_id = '{GLOBAL_ORG_UNIT_ROOT_ID}'::uuid
            WHERE upper(valid_time) IS NULL
              AND deleted_at IS NULL
              AND branch = 'main'
              AND organizational_unit_id IS NULL
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema.

    Drops the new tables and the projects attribution columns. The data seeds
    (GLOBAL org unit, EUR rate) and the projects backfill are NOT reversed —
    they are non-destructive data operations and undoing them could discard
    user edits applied after the upgrade (mirrors c93e9767de59's convention).
    """
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_projects_project_manager_id"))
        batch_op.drop_index(batch_op.f("ix_projects_organizational_unit_id"))
        batch_op.drop_index(batch_op.f("ix_projects_customer_id"))
        batch_op.drop_column("customer_id")
        batch_op.drop_column("project_manager_id")
        batch_op.drop_column("organizational_unit_id")

    with op.batch_alter_table("currency_rates", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_currency_rates_effective_date"))
        batch_op.drop_index(batch_op.f("ix_currency_rates_currency"))
    op.drop_table("currency_rates")

    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.drop_index("uq_customers_code_active")
        batch_op.drop_index(batch_op.f("ix_customers_code"))
    op.drop_table("customers")
