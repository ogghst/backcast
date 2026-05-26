"""Performance benchmarks for UnifiedRBACService.

Measures cached/cold permission checks, bulk role loading, and cache
invalidation latency against a real database.

Targets: cached < 5 ms, cold < 50 ms, invalidation < 1 ms.
"""

import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac_unified import UnifiedRBACService, rbac_session
from app.models.domain.rbac import RBACRole, RBACRolePermission
from app.models.domain.user import User
from app.models.domain.user_role_assignment import ScopeType, UserRoleAssignment

pytestmark = pytest.mark.performance

_ROLE_DEFS: list[tuple[str, list[str]]] = [
    (
        "admin",
        [
            "project-read",
            "project-write",
            "cost-element-read",
            "cost-element-write",
            "user-manage",
        ],
    ),
    (
        "manager",
        ["project-read", "cost-element-read", "cost-element-write", "forecast-create"],
    ),
    ("viewer", ["project-read", "cost-element-read"]),
]
_NUM_USERS = 10


@pytest_asyncio.fixture
async def bench_rbac_service(db_session: AsyncSession) -> UnifiedRBACService:
    """Seed RBAC tables and return a service with warm permissions cache."""
    service = UnifiedRBACService()

    # -- roles + permissions (idempotent: skip if already exist from seed data) --
    role_map: dict[str, RBACRole] = {}
    for name, _perms in _ROLE_DEFS:
        existing = await db_session.execute(
            select(RBACRole).where(RBACRole.name == name)
        )
        role = existing.scalar_one_or_none()
        if role is None:
            role = RBACRole(id=uuid4(), name=name, is_system=True)
            db_session.add(role)
            await db_session.flush()
        role_map[name] = role

    for name, perms in _ROLE_DEFS:
        for perm in perms:
            existing = await db_session.execute(
                select(RBACRolePermission).where(
                    RBACRolePermission.role_id == role_map[name].id,
                    RBACRolePermission.permission == perm,
                )
            )
            if existing.scalar_one_or_none() is None:
                db_session.add(
                    RBACRolePermission(
                        id=uuid4(), role_id=role_map[name].id, permission=perm
                    )
                )
    await db_session.flush()

    # -- users --
    user_ids: list[UUID] = []
    for i in range(_NUM_USERS):
        uid = uuid4()
        user_ids.append(uid)
        db_session.add(
            User(
                id=uuid4(),
                user_id=uid,
                email=f"bench-user-{i}@test.com",
                full_name=f"Bench User {i}",
                is_active=True,
                hashed_password="x",
                created_by=uuid4(),
            )
        )
    await db_session.flush()

    # -- assignments (spread roles across users) --
    for i, uid in enumerate(user_ids):
        role_name = _ROLE_DEFS[i % len(_ROLE_DEFS)][0]
        db_session.add(
            UserRoleAssignment(
                id=uuid4(),
                user_id=uid,
                role_id=role_map[role_name].id,
                scope_type=ScopeType.GLOBAL,
                scope_id=None,
                granted_at=datetime.now(UTC),
            )
        )
    await db_session.flush()

    # Warm the permissions cache
    async with rbac_session(db_session):
        await service.refresh_permissions_cache()

    return service


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cached_permission_check(
    db_session: AsyncSession,
    bench_rbac_service: UnifiedRBACService,
) -> None:
    """Cached has_permission() must complete in < 5 ms."""
    service = bench_rbac_service
    result = await db_session.execute(UserRoleAssignment.__table__.select().limit(1))
    row = result.first()
    assert row is not None
    user_id = row.user_id

    timings: list[float] = []
    async with rbac_session(db_session):
        # Warm assignment cache with one call
        await service.has_permission(user_id, "project-read")
        for _ in range(100):
            start = time.perf_counter()
            await service.has_permission(user_id, "project-read")
            timings.append((time.perf_counter() - start) * 1000)

    avg = sum(timings) / len(timings)
    p95 = sorted(timings)[94]
    print(f"\n[cached] avg={avg:.2f}ms  p95={p95:.2f}ms  n={len(timings)}")
    assert avg < 5, f"Cached avg {avg:.2f}ms exceeds 5ms target"


@pytest.mark.asyncio
async def test_cold_permission_check(
    db_session: AsyncSession,
    bench_rbac_service: UnifiedRBACService,
) -> None:
    """Cold (cache-miss) has_permission() must complete in < 50 ms."""
    service = bench_rbac_service
    result = await db_session.execute(UserRoleAssignment.__table__.select().limit(1))
    row = result.first()
    assert row is not None
    user_id = row.user_id

    timings: list[float] = []
    for _ in range(20):
        service._assignment_cache.clear()
        async with rbac_session(db_session):
            start = time.perf_counter()
            await service.has_permission(user_id, "project-read")
            timings.append((time.perf_counter() - start) * 1000)

    avg = sum(timings) / len(timings)
    p95 = sorted(timings)[18]
    print(f"\n[cold] avg={avg:.2f}ms  p95={p95:.2f}ms  n={len(timings)}")
    assert avg < 50, f"Cold avg {avg:.2f}ms exceeds 50ms target"


@pytest.mark.asyncio
async def test_bulk_assignment_loading(
    db_session: AsyncSession,
    bench_rbac_service: UnifiedRBACService,
) -> None:
    """get_user_roles() across 50 user-scope combos must each be < 50 ms."""
    service = bench_rbac_service
    result = await db_session.execute(UserRoleAssignment.__table__.select())
    rows = result.all()

    combos: list[tuple[UUID, str, UUID | None]] = []
    for row in rows:
        combos.append((row.user_id, ScopeType.GLOBAL, None))
    # Pad to >= 50 with synthetic scope lookups (cache-miss, returns [])
    base_uid = rows[0].user_id
    for _ in range(50 - len(combos)):
        combos.append((base_uid, ScopeType.PROJECT, uuid4()))

    timings: list[float] = []
    async with rbac_session(db_session):
        for uid, stype, sid in combos:
            start = time.perf_counter()
            await service.get_user_roles(uid, stype, sid)
            timings.append((time.perf_counter() - start) * 1000)

    avg = sum(timings) / len(timings)
    worst = max(timings)
    print(f"\n[bulk] avg={avg:.2f}ms  worst={worst:.2f}ms  n={len(timings)}")
    assert worst < 50, f"Bulk worst {worst:.2f}ms exceeds 50ms target"


@pytest.mark.asyncio
async def test_cache_invalidation_performance(
    db_session: AsyncSession,
    bench_rbac_service: UnifiedRBACService,
) -> None:
    """Cache invalidation must complete in < 1 ms per call."""
    service = bench_rbac_service
    uid = uuid4()

    # Populate cache with synthetic entries
    for _ in range(100):
        service._assignment_cache[(uid, "project", uuid4())] = (
            ["manager"],
            datetime.now(UTC),
        )

    # Single-scope invalidation
    start = time.perf_counter()
    service._invalidate_assignment_cache(uid, scope_type="project")
    t_single = (time.perf_counter() - start) * 1000

    # Re-populate for full-user invalidation
    for _ in range(100):
        service._assignment_cache[(uid, "global", None)] = (
            ["admin"],
            datetime.now(UTC),
        )
        service._assignment_cache[(uid, "project", uuid4())] = (
            ["viewer"],
            datetime.now(UTC),
        )

    start = time.perf_counter()
    service._invalidate_assignment_cache(uid)
    t_full = (time.perf_counter() - start) * 1000

    assert t_single < 1, f"Single-scope invalidation {t_single:.3f}ms exceeds 1ms"
    assert t_full < 1, f"Full-user invalidation {t_full:.3f}ms exceeds 1ms"
    print(f"\n[invalidate] single-scope={t_single:.3f}ms  full-user={t_full:.3f}ms")
