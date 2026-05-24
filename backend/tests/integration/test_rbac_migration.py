"""Verification tests for the unified RBAC data migration.

Tests the SQL logic from 20260510_unified_rbac_data.py that migrates:
- User.role -> UserRoleAssignment (scope_type='global')
- ProjectMember -> UserRoleAssignment (scope_type='project')

Since the old schema (users.role column, project_members table) no longer exists,
these tests create temporary tables to simulate the pre-migration state and verify
the migration SQL logic is correct.

Addresses: TD-095
"""

import pytest
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Schema verification tests (run against current DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.migration
async def test_rbac_roles_seeded(db_session):
    """Verify all expected roles were seeded into rbac_roles table."""
    result = await db_session.execute(
        text("SELECT name FROM rbac_roles ORDER BY name")
    )
    role_names = {row[0] for row in result.all()}

    expected_roles = {
        "admin",
        "manager",
        "viewer",
        "ai-viewer",
        "ai-manager",
        "ai-admin",
        "change_order_approver",
    }
    assert expected_roles.issubset(role_names), (
        f"Missing seeded roles: {expected_roles - role_names}"
    )


@pytest.mark.asyncio
@pytest.mark.migration
async def test_user_role_assignments_schema(db_session):
    """Verify user_role_assignments table has the expected columns and types."""
    result = await db_session.execute(
        text(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'user_role_assignments' "
            "ORDER BY ordinal_position"
        )
    )
    columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.all()}

    required = {
        "id": {"type": "uuid", "nullable": "NO"},
        "user_id": {"type": "uuid", "nullable": "NO"},
        "role_id": {"type": "uuid", "nullable": "NO"},
        "scope_type": {"type": "character varying", "nullable": "NO"},
        "scope_id": {"type": "uuid", "nullable": "YES"},
        "metadata": {"type": "jsonb", "nullable": "YES"},
        "granted_by": {"type": "uuid", "nullable": "YES"},
        "granted_at": {"type": "timestamp with time zone", "nullable": "NO"},
        "expires_at": {"type": "timestamp with time zone", "nullable": "YES"},
        "created_at": {"type": "timestamp with time zone", "nullable": "NO"},
        "updated_at": {"type": "timestamp with time zone", "nullable": "NO"},
    }

    for col_name, expected in required.items():
        assert col_name in columns, f"Column '{col_name}' missing"
        actual = columns[col_name]
        assert actual["type"] == expected["type"], (
            f"Column '{col_name}' wrong type: {actual['type']} != {expected['type']}"
        )
        assert actual["nullable"] == expected["nullable"], (
            f"Column '{col_name}' wrong nullable: {actual['nullable']} != {expected['nullable']}"
        )


@pytest.mark.asyncio
@pytest.mark.migration
async def test_user_role_assignments_primary_key(db_session):
    """Verify the primary key constraint on user_role_assignments."""
    result = await db_session.execute(
        text(
            "SELECT pg_get_constraintdef(c.oid) "
            "FROM pg_constraint c "
            "JOIN pg_class cl ON cl.oid = c.conrelid "
            "WHERE cl.relname = 'user_role_assignments' "
            "AND contype = 'p'"
        )
    )
    pk_def = result.scalar_one()
    assert "id" in pk_def, "Primary key on id not found"


@pytest.mark.asyncio
@pytest.mark.migration
async def test_user_role_assignments_fk_to_rbac_roles(db_session):
    """Verify FK constraint from user_role_assignments.role_id to rbac_roles.id."""
    result = await db_session.execute(
        text(
            "SELECT pg_get_constraintdef(c.oid) "
            "FROM pg_constraint c "
            "JOIN pg_class cl ON cl.oid = c.conrelid "
            "WHERE cl.relname = 'user_role_assignments' "
            "AND contype = 'f'"
        )
    )
    fk_defs = [row[0] for row in result.all()]
    assert any("rbac_roles" in fk for fk in fk_defs), (
        "No foreign key to rbac_roles found on user_role_assignments"
    )


# ---------------------------------------------------------------------------
# Migration logic tests (using temporary tables to simulate old schema)
# ---------------------------------------------------------------------------


async def _setup_old_users_table(db_session):
    """Create a temp table simulating the old users table with a role column."""
    await db_session.execute(text("""
        CREATE TEMP TABLE _test_old_users (
            user_id UUID NOT NULL,
            role VARCHAR,
            deleted_at TIMESTAMPTZ,
            valid_time TSTZRANGE NOT NULL,
            transaction_time TSTZRANGE NOT NULL
        )
    """))


async def _setup_old_project_members_table(db_session):
    """Create a temp table simulating the old project_members table."""
    await db_session.execute(text("""
        CREATE TEMP TABLE _test_old_project_members (
            user_id UUID NOT NULL,
            project_id UUID NOT NULL,
            role VARCHAR NOT NULL,
            assigned_by UUID,
            assigned_at TIMESTAMPTZ
        )
    """))


# -- Global role migration (User.role -> UserRoleAssignment) --


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_global_from_users(db_session):
    """Verify User.role -> UserRoleAssignment migration for scope_type='global'."""
    await _setup_old_users_table(db_session)

    from uuid import uuid4

    user_a = uuid4()
    user_b = uuid4()

    await db_session.execute(
        text("""
        INSERT INTO _test_old_users (user_id, role, deleted_at, valid_time, transaction_time)
        VALUES
            (:uid_a, 'admin', NULL,
             tstzrange(CURRENT_TIMESTAMP - interval '1 year', NULL),
             tstzrange(CURRENT_TIMESTAMP, NULL)),
            (:uid_b, 'viewer', NULL,
             tstzrange(CURRENT_TIMESTAMP - interval '1 year', NULL),
             tstzrange(CURRENT_TIMESTAMP, NULL))
        """),
        {"uid_a": user_a, "uid_b": user_b},
    )

    await db_session.execute(text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            sub.root_id,
            r.id,
            'global',
            NULL,
            NULL,
            NULL,
            now(),
            NULL,
            now(),
            now()
        FROM (
            SELECT DISTINCT ON (user_id)
                user_id AS root_id, role
            FROM _test_old_users
            WHERE deleted_at IS NULL
              AND valid_time @> CURRENT_TIMESTAMP
              AND upper_inf(transaction_time)
            ORDER BY user_id, valid_time DESC
        ) sub
        JOIN rbac_roles r ON r.name = sub.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = sub.root_id
              AND ura.scope_type = 'global'
              AND ura.scope_id IS NULL
        )
    """))

    result = await db_session.execute(
        text(
            "SELECT ura.user_id, r.name "
            "FROM user_role_assignments ura "
            "JOIN rbac_roles r ON r.id = ura.role_id "
            "WHERE ura.scope_type = 'global' "
            "AND ura.user_id IN (:uid_a, :uid_b) "
            "ORDER BY r.name"
        ),
        {"uid_a": user_a, "uid_b": user_b},
    )
    assignments = {row[1]: row[0] for row in result.all()}

    assert "admin" in assignments, "Admin global assignment not created"
    assert assignments["admin"] == user_a
    assert "viewer" in assignments, "Viewer global assignment not created"
    assert assignments["viewer"] == user_b

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_users"))


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_global_idempotent(db_session):
    """Verify running the global migration twice creates no duplicates."""
    await _setup_old_users_table(db_session)

    from uuid import uuid4

    user_id = uuid4()

    await db_session.execute(
        text("""
        INSERT INTO _test_old_users (user_id, role, deleted_at, valid_time, transaction_time)
        VALUES (:uid, 'manager', NULL,
                tstzrange(CURRENT_TIMESTAMP - interval '1 year', NULL),
                tstzrange(CURRENT_TIMESTAMP, NULL))
        """),
        {"uid": user_id},
    )

    migration_sql = text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            sub.root_id,
            r.id,
            'global',
            NULL,
            NULL,
            NULL,
            now(),
            NULL,
            now(),
            now()
        FROM (
            SELECT DISTINCT ON (user_id)
                user_id AS root_id, role
            FROM _test_old_users
            WHERE deleted_at IS NULL
              AND valid_time @> CURRENT_TIMESTAMP
              AND upper_inf(transaction_time)
            ORDER BY user_id, valid_time DESC
        ) sub
        JOIN rbac_roles r ON r.name = sub.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = sub.root_id
              AND ura.scope_type = 'global'
              AND ura.scope_id IS NULL
        )
    """)

    await db_session.execute(migration_sql)
    await db_session.execute(migration_sql)

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'global'"
        ),
        {"uid": user_id},
    )
    count = result.scalar_one()
    assert count == 1, f"Expected 1 assignment after double-run, got {count}"

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_users"))


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_skips_deleted_users(db_session):
    """Verify users with deleted_at set are skipped during migration."""
    await _setup_old_users_table(db_session)

    from uuid import uuid4

    active_user = uuid4()
    deleted_user = uuid4()

    await db_session.execute(
        text("""
        INSERT INTO _test_old_users (user_id, role, deleted_at, valid_time, transaction_time)
        VALUES
            (:active, 'admin', NULL,
             tstzrange(CURRENT_TIMESTAMP - interval '1 year', NULL),
             tstzrange(CURRENT_TIMESTAMP, NULL)),
            (:deleted, 'manager', CURRENT_TIMESTAMP,
             tstzrange(CURRENT_TIMESTAMP - interval '1 year', NULL),
             tstzrange(CURRENT_TIMESTAMP, NULL))
        """),
        {"active": active_user, "deleted": deleted_user},
    )

    await db_session.execute(text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            sub.root_id,
            r.id,
            'global',
            NULL,
            NULL,
            NULL,
            now(),
            NULL,
            now(),
            now()
        FROM (
            SELECT DISTINCT ON (user_id)
                user_id AS root_id, role
            FROM _test_old_users
            WHERE deleted_at IS NULL
              AND valid_time @> CURRENT_TIMESTAMP
              AND upper_inf(transaction_time)
            ORDER BY user_id, valid_time DESC
        ) sub
        JOIN rbac_roles r ON r.name = sub.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = sub.root_id
              AND ura.scope_type = 'global'
              AND ura.scope_id IS NULL
        )
    """))

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'global'"
        ),
        {"uid": active_user},
    )
    assert result.scalar_one() == 1

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'global'"
        ),
        {"uid": deleted_user},
    )
    assert result.scalar_one() == 0

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_users"))


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_skips_unknown_role(db_session):
    """Verify users with a role not in rbac_roles are silently skipped."""
    await _setup_old_users_table(db_session)

    from uuid import uuid4

    user_id = uuid4()

    await db_session.execute(
        text("""
        INSERT INTO _test_old_users (user_id, role, deleted_at, valid_time, transaction_time)
        VALUES (:uid, 'nonexistent_role', NULL,
                tstzrange(CURRENT_TIMESTAMP - interval '1 year', NULL),
                tstzrange(CURRENT_TIMESTAMP, NULL))
        """),
        {"uid": user_id},
    )

    await db_session.execute(text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            sub.root_id,
            r.id,
            'global',
            NULL,
            NULL,
            NULL,
            now(),
            NULL,
            now(),
            now()
        FROM (
            SELECT DISTINCT ON (user_id)
                user_id AS root_id, role
            FROM _test_old_users
            WHERE deleted_at IS NULL
              AND valid_time @> CURRENT_TIMESTAMP
              AND upper_inf(transaction_time)
            ORDER BY user_id, valid_time DESC
        ) sub
        JOIN rbac_roles r ON r.name = sub.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = sub.root_id
              AND ura.scope_type = 'global'
              AND ura.scope_id IS NULL
        )
    """))

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'global'"
        ),
        {"uid": user_id},
    )
    assert result.scalar_one() == 0, "Assignment should not exist for unknown role"

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_users"))


# -- Project member migration (ProjectMember -> UserRoleAssignment) --


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_project_from_project_members(db_session):
    """Verify ProjectMember -> UserRoleAssignment migration for scope_type='project'."""
    await _setup_old_project_members_table(db_session)

    from uuid import uuid4

    user_id = uuid4()
    project_id = uuid4()
    assigned_by = uuid4()

    await db_session.execute(
        text("""
        INSERT INTO _test_old_project_members (user_id, project_id, role, assigned_by, assigned_at)
        VALUES (:uid, :pid, 'viewer', :by, CURRENT_TIMESTAMP - interval '1 day')
        """),
        {"uid": user_id, "pid": project_id, "by": assigned_by},
    )

    await db_session.execute(text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            pm.user_id,
            r.id,
            'project',
            pm.project_id,
            NULL,
            pm.assigned_by,
            COALESCE(pm.assigned_at, now()),
            NULL,
            now(),
            now()
        FROM _test_old_project_members pm
        JOIN rbac_roles r ON r.name = pm.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = pm.user_id
              AND ura.scope_type = 'project'
              AND ura.scope_id = pm.project_id
        )
    """))

    result = await db_session.execute(
        text(
            "SELECT ura.user_id, r.name, ura.scope_id, ura.granted_by "
            "FROM user_role_assignments ura "
            "JOIN rbac_roles r ON r.id = ura.role_id "
            "WHERE ura.scope_type = 'project' "
            "AND ura.user_id = :uid"
        ),
        {"uid": user_id},
    )
    row = result.first()
    assert row is not None, "Project assignment not created"
    assert row[1] == "viewer"
    assert row[2] == project_id
    assert row[3] == assigned_by

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_project_members"))


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_project_idempotent(db_session):
    """Verify running the project migration twice creates no duplicates."""
    await _setup_old_project_members_table(db_session)

    from uuid import uuid4

    user_id = uuid4()
    project_id = uuid4()

    await db_session.execute(
        text("""
        INSERT INTO _test_old_project_members (user_id, project_id, role)
        VALUES (:uid, :pid, 'admin')
        """),
        {"uid": user_id, "pid": project_id},
    )

    migration_sql = text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            pm.user_id,
            r.id,
            'project',
            pm.project_id,
            NULL,
            pm.assigned_by,
            COALESCE(pm.assigned_at, now()),
            NULL,
            now(),
            now()
        FROM _test_old_project_members pm
        JOIN rbac_roles r ON r.name = pm.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = pm.user_id
              AND ura.scope_type = 'project'
              AND ura.scope_id = pm.project_id
        )
    """)

    await db_session.execute(migration_sql)
    await db_session.execute(migration_sql)

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'project' AND scope_id = :pid"
        ),
        {"uid": user_id, "pid": project_id},
    )
    assert result.scalar_one() == 1

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_project_members"))


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_project_null_assigned_at(db_session):
    """Verify COALESCE handles NULL assigned_at by using now()."""
    await _setup_old_project_members_table(db_session)

    from uuid import uuid4

    user_id = uuid4()
    project_id = uuid4()

    await db_session.execute(
        text("""
        INSERT INTO _test_old_project_members (user_id, project_id, role)
        VALUES (:uid, :pid, 'viewer')
        """),
        {"uid": user_id, "pid": project_id},
    )

    await db_session.execute(text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            pm.user_id,
            r.id,
            'project',
            pm.project_id,
            NULL,
            pm.assigned_by,
            COALESCE(pm.assigned_at, now()),
            NULL,
            now(),
            now()
        FROM _test_old_project_members pm
        JOIN rbac_roles r ON r.name = pm.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = pm.user_id
              AND ura.scope_type = 'project'
              AND ura.scope_id = pm.project_id
        )
    """))

    result = await db_session.execute(
        text(
            "SELECT granted_at FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'project' AND scope_id = :pid"
        ),
        {"uid": user_id, "pid": project_id},
    )
    granted_at = result.scalar_one()
    assert granted_at is not None, "granted_at should fallback to now() when NULL"

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_project_members"))


# -- Downgrade logic tests --


@pytest.mark.asyncio
@pytest.mark.migration
async def test_downgrade_removes_project_migrated_data(db_session):
    """Verify downgrade SQL removes project-scoped assignments with granted_by set."""
    from uuid import uuid4

    user_id = uuid4()
    project_id = uuid4()
    role_id_result = await db_session.execute(
        text("SELECT id FROM rbac_roles WHERE name = 'viewer' LIMIT 1")
    )
    role_id = role_id_result.scalar_one()

    await db_session.execute(
        text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(), :uid, :rid, 'project', :pid,
            NULL, :by, now(), NULL, now(), now()
        )
        """),
        {"uid": user_id, "rid": role_id, "pid": project_id, "by": uuid4()},
    )

    await db_session.execute(text("""
        DELETE FROM user_role_assignments
        WHERE scope_type = 'project'
          AND granted_by IS NOT NULL
    """))

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'project'"
        ),
        {"uid": user_id},
    )
    assert result.scalar_one() == 0, "Migrated project assignment should be deleted"


@pytest.mark.asyncio
@pytest.mark.migration
async def test_downgrade_removes_global_migrated_data(db_session):
    """Verify downgrade SQL removes global assignments matching migration pattern."""
    from uuid import uuid4

    user_id = uuid4()
    role_id_result = await db_session.execute(
        text("SELECT id FROM rbac_roles WHERE name = 'manager' LIMIT 1")
    )
    role_id = role_id_result.scalar_one()

    await db_session.execute(
        text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(), :uid, :rid, 'global', NULL,
            NULL, NULL, now(), NULL, now(), now()
        )
        """),
        {"uid": user_id, "rid": role_id},
    )

    await db_session.execute(text("""
        DELETE FROM user_role_assignments
        WHERE scope_type = 'global'
          AND scope_id IS NULL
          AND metadata IS NULL
    """))

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'global'"
        ),
        {"uid": user_id},
    )
    assert result.scalar_one() == 0, "Migrated global assignment should be deleted"


@pytest.mark.asyncio
@pytest.mark.migration
async def test_downgrade_preserves_manual_assignments(db_session):
    """Verify downgrade SQL does NOT delete manually-created assignments."""
    from uuid import uuid4

    user_global = uuid4()
    user_project = uuid4()
    project_id = uuid4()

    role_id_result = await db_session.execute(
        text("SELECT id FROM rbac_roles WHERE name = 'admin' LIMIT 1")
    )
    role_id = role_id_result.scalar_one()

    # Manual global assignment (has metadata)
    await db_session.execute(
        text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(), :uid, :rid, 'global', NULL,
            '{"source": "manual"}'::jsonb, NULL, now(), NULL, now(), now()
        )
        """),
        {"uid": user_global, "rid": role_id},
    )

    # Manual project assignment (no granted_by)
    await db_session.execute(
        text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(), :uid, :rid, 'project', :pid,
            NULL, NULL, now(), NULL, now(), now()
        )
        """),
        {"uid": user_project, "rid": role_id, "pid": project_id},
    )

    # Run both downgrade SQLs
    await db_session.execute(text("""
        DELETE FROM user_role_assignments
        WHERE scope_type = 'project'
          AND granted_by IS NOT NULL
    """))
    await db_session.execute(text("""
        DELETE FROM user_role_assignments
        WHERE scope_type = 'global'
          AND scope_id IS NULL
          AND metadata IS NULL
    """))

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'global'"
        ),
        {"uid": user_global},
    )
    assert result.scalar_one() == 1, "Manual global assignment should survive downgrade"

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'project'"
        ),
        {"uid": user_project},
    )
    assert result.scalar_one() == 1, "Manual project assignment should survive downgrade"


# -- Edge case tests --


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_skips_null_role(db_session):
    """Verify users with NULL role are skipped (JOIN on rbac_roles.name fails)."""
    await _setup_old_users_table(db_session)

    from uuid import uuid4

    user_id = uuid4()

    await db_session.execute(
        text("""
        INSERT INTO _test_old_users (user_id, role, deleted_at, valid_time, transaction_time)
        VALUES (:uid, NULL, NULL,
                tstzrange(CURRENT_TIMESTAMP - interval '1 year', NULL),
                tstzrange(CURRENT_TIMESTAMP, NULL))
        """),
        {"uid": user_id},
    )

    await db_session.execute(text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            sub.root_id,
            r.id,
            'global',
            NULL,
            NULL,
            NULL,
            now(),
            NULL,
            now(),
            now()
        FROM (
            SELECT DISTINCT ON (user_id)
                user_id AS root_id, role
            FROM _test_old_users
            WHERE deleted_at IS NULL
              AND valid_time @> CURRENT_TIMESTAMP
              AND upper_inf(transaction_time)
            ORDER BY user_id, valid_time DESC
        ) sub
        JOIN rbac_roles r ON r.name = sub.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = sub.root_id
              AND ura.scope_type = 'global'
              AND ura.scope_id IS NULL
        )
    """))

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'global'"
        ),
        {"uid": user_id},
    )
    assert result.scalar_one() == 0, "No assignment should exist for NULL role"

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_users"))


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_picks_latest_user_version(db_session):
    """Verify DISTINCT ON picks the latest valid_time version of a user."""
    await _setup_old_users_table(db_session)

    from uuid import uuid4

    user_id = uuid4()

    # Old version: viewer, valid 2024-01-01 to 2024-06-01
    await db_session.execute(
        text("""
        INSERT INTO _test_old_users (user_id, role, deleted_at, valid_time, transaction_time)
        VALUES (:uid, 'viewer', NULL,
                tstzrange('2024-01-01'::timestamptz, '2024-06-01'::timestamptz),
                tstzrange(CURRENT_TIMESTAMP, NULL))
        """),
        {"uid": user_id},
    )
    # Current version: admin, valid from 2024-06-01 to infinity
    await db_session.execute(
        text("""
        INSERT INTO _test_old_users (user_id, role, deleted_at, valid_time, transaction_time)
        VALUES (:uid, 'admin', NULL,
                tstzrange('2024-06-01'::timestamptz, NULL),
                tstzrange(CURRENT_TIMESTAMP, NULL))
        """),
        {"uid": user_id},
    )

    await db_session.execute(text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            sub.root_id,
            r.id,
            'global',
            NULL,
            NULL,
            NULL,
            now(),
            NULL,
            now(),
            now()
        FROM (
            SELECT DISTINCT ON (user_id)
                user_id AS root_id, role
            FROM _test_old_users
            WHERE deleted_at IS NULL
              AND valid_time @> CURRENT_TIMESTAMP
              AND upper_inf(transaction_time)
            ORDER BY user_id, valid_time DESC
        ) sub
        JOIN rbac_roles r ON r.name = sub.role
        WHERE NOT EXISTS (
            SELECT 1 FROM user_role_assignments ura
            WHERE ura.user_id = sub.root_id
              AND ura.scope_type = 'global'
              AND ura.scope_id IS NULL
        )
    """))

    result = await db_session.execute(
        text(
            "SELECT r.name FROM user_role_assignments ura "
            "JOIN rbac_roles r ON r.id = ura.role_id "
            "WHERE ura.user_id = :uid AND ura.scope_type = 'global'"
        ),
        {"uid": user_id},
    )
    role_name = result.scalar_one()
    assert role_name == "admin", f"Expected 'admin' (current version), got '{role_name}'"

    await db_session.execute(text("DROP TABLE IF EXISTS _test_old_users"))


@pytest.mark.asyncio
@pytest.mark.migration
async def test_downgrade_imprecision_warning(db_session):
    """Document the downgrade's imprecise deletion pattern.

    The downgrade deletes project assignments WHERE granted_by IS NOT NULL,
    which could delete manually-created assignments that happen to have
    granted_by set. This test documents the known limitation.
    """
    from uuid import uuid4

    user_id = uuid4()
    project_id = uuid4()
    admin_id = uuid4()

    role_id_result = await db_session.execute(
        text("SELECT id FROM rbac_roles WHERE name = 'viewer' LIMIT 1")
    )
    role_id = role_id_result.scalar_one()

    # Simulate a manually-created assignment that happens to have granted_by set
    await db_session.execute(
        text("""
        INSERT INTO user_role_assignments (
            id, user_id, role_id, scope_type, scope_id,
            metadata, granted_by, granted_at, expires_at,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(), :uid, :rid, 'project', :pid,
            '{"source": "admin_ui"}'::jsonb, :by, now(), NULL, now(), now()
        )
        """),
        {"uid": user_id, "rid": role_id, "pid": project_id, "by": admin_id},
    )

    # Downgrade deletes ALL project assignments with granted_by IS NOT NULL
    await db_session.execute(text("""
        DELETE FROM user_role_assignments
        WHERE scope_type = 'project'
          AND granted_by IS NOT NULL
    """))

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM user_role_assignments "
            "WHERE user_id = :uid AND scope_type = 'project'"
        ),
        {"uid": user_id},
    )
    # This documents the behavior: the manual assignment WAS deleted
    # because it has granted_by set, even though it has metadata.
    count = result.scalar_one()
    assert count == 0, (
        "Known limitation: downgrade deletes project assignments with granted_by, "
        "even if they were manually created. The metadata field is not checked."
    )
