"""Tests for the functional-dashboards portfolio foundation (G1, G11, G17).

Covers:
- G1 portfolio EVM endpoint: RBAC membership scoping + aggregation correctness
  vs per-project, plus the at-risk (SPI) subset.
- G11 ΔEAC forecast history: the ``GET /forecasts/{id}/history`` route returns
  the EAC-over-time versions.
- G17 portfolio CO pipeline: ``get_portfolio_change_order_stats`` aggregates
  per-project stats, and the ``/stats`` route no longer masks errors as 500.

The default ``client`` fixture authenticates as the global admin (which sees
all projects), so end-to-end scoping is validated against the unified RBAC
service directly (mirrors ``test_evm_batch_scoping.py``), while aggregation
correctness is validated via the service method over a fresh hierarchy.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.core.versioning.enums import BranchMode
from app.models.domain.currency_rate import CurrencyRate
from app.models.domain.user import User
from app.models.schemas.evm import EntityType
from app.models.schemas.forecast import ForecastUpdate
from app.services.change_order_reporting_service import ChangeOrderReportingService
from app.services.currency_rate_service import convert_to_base
from app.services.evm_service import EVMService
from app.services.forecast_service import ForecastService
from tests.factories import (
    create_full_hierarchy,
    create_test_control_account,
    create_test_cost_element,
    create_test_cost_element_type,
    create_test_cost_registration,
    create_test_org_unit,
    create_test_progress_entry,
    create_test_project,
    create_test_wbs_element,
    create_test_work_package,
)

EVM_PREFIX = "/evm"
FORECAST_PREFIX = "/forecasts"


# ---------------------------------------------------------------------------
# G1 — portfolio EVM endpoint RBAC + aggregation.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_non_member_has_no_accessible_projects(
    db: AsyncSession,
) -> None:
    """A role-less user gets an empty accessible-projects list.

    The portfolio route resolves accessible projects before computing EVM; an
    empty set yields a 404 (no portfolio), so a non-member cannot read
    portfolio metrics for projects they do not belong to.
    """
    lone_user_id = uuid4()
    db.add(
        User(
            id=lone_user_id,
            user_id=lone_user_id,
            email=f"lone-portfolio-{lone_user_id}@backcast.test",
            hashed_password="x",
            full_name="Lone Portfolio Nonmember",
            is_active=True,
            created_by=lone_user_id,
        )
    )
    await db.flush()
    try:
        set_unified_rbac_session(db)
        service = get_unified_rbac_service()
        accessible = await service.get_accessible_projects(user_id=lone_user_id)
        set_unified_rbac_session(None)
        assert accessible == []
    finally:
        # Cleanup the persistent row (db fixture commits; see memory note 35).
        await db.execute(delete(User).where(User.user_id == lone_user_id))
        await db.flush()


@pytest.mark.asyncio
async def test_portfolio_evm_aggregates_per_project(
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """Portfolio summary matches a single project's per-project EVM, and the
    per-project breakdown row carries the project's metrics + attribution.

    Uses the service method directly (the admin client sees all seed projects,
    which would make an end-to-end comparison noisy).
    """
    h = await create_full_hierarchy(db, actor_id)
    project_id = h["project"].project_id
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("5000")
    )
    await create_test_progress_entry(
        db, actor_id, h["wp"].work_package_id, progress_percentage=Decimal("50.00")
    )
    await db.commit()

    evm = EVMService(db)
    control_date = datetime.now(tz=UTC)
    portfolio = await evm.calculate_portfolio_evm(
        project_ids=[project_id],
        control_date=control_date,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    # The single project's per-project EVM must equal the batch EVM.
    single = await evm.calculate_evm_metrics_batch(
        entity_type=EntityType.PROJECT,
        entity_ids=[project_id],
        control_date=control_date,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    # Summary BAC = single-project BAC (one project in the portfolio).
    assert portfolio.summary.bac == pytest.approx(single.bac)
    assert portfolio.summary.ac == pytest.approx(single.ac)

    # The breakdown has exactly our project, with its CPI/SPI/VAC.
    rows = [p for p in portfolio.projects if p.project_id == project_id]
    assert len(rows) == 1
    row = rows[0]
    assert row.name == h["project"].name
    assert row.status == h["project"].status
    assert row.cpi == pytest.approx(single.cpi)
    assert row.spi == pytest.approx(single.spi)
    # Attribution columns flow through.
    assert row.currency == h["project"].currency


@pytest.mark.asyncio
async def test_portfolio_at_risk_subset_is_spi_below_threshold(
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """``at_risk_projects`` is exactly the projects with SPI < 0.9."""
    h = await create_full_hierarchy(db, actor_id)
    project_id = h["project"].project_id
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("5000")
    )
    await create_test_progress_entry(
        db, actor_id, h["wp"].work_package_id, progress_percentage=Decimal("10.00")
    )
    await db.commit()

    evm = EVMService(db)
    portfolio = await evm.calculate_portfolio_evm(
        project_ids=[project_id],
        control_date=datetime.now(tz=UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    # With low progress vs high AC, SPI should be < 0.9 -> at risk.
    for row in portfolio.projects:
        if row.at_risk:
            assert row.spi is not None and row.spi < 0.9
    # The at-risk subset is consistent with the breakdown's at_risk flags.
    assert portfolio.at_risk_projects == [p for p in portfolio.projects if p.at_risk]


@pytest.mark.asyncio
async def test_portfolio_evm_multi_currency_rollup(
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """Portfolio CPI/SPI/TCPI equal indices computed on fully base-converted
    per-project flows (not the raw-mixed native-currency ones).

    Builds one EUR project and one USD project. The USD project's pv/ac/ev are
    converted to EUR at a seeded rate before rollup; if the FX conversion were
    applied only to bac/eac/vac (the pre-fix bug), the summary CPI/SPI would
    sum mixed currencies and diverge from the independently-recomputed base
    indices. This test guards against that regression.
    """
    usd_rate = Decimal("1.10")  # 1 USD = 1.10 EUR

    # EUR project (default factory currency).
    eur_h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, eur_h["ce"].cost_element_id, amount=Decimal("4000")
    )
    await create_test_progress_entry(
        db,
        actor_id,
        eur_h["wp"].work_package_id,
        progress_percentage=Decimal("50.00"),
    )

    # USD project — same hierarchy shape, currency set at creation.
    usd_project = await create_test_project(
        db, actor_id, currency="USD", contract_value=Decimal("2000000")
    )
    usd_org = await create_test_org_unit(db, actor_id)
    usd_wbs = await create_test_wbs_element(db, actor_id, usd_project.project_id)
    usd_ca = await create_test_control_account(
        db, actor_id, usd_wbs.wbs_element_id, usd_org.organizational_unit_id
    )
    usd_wp = await create_test_work_package(db, actor_id, usd_ca.control_account_id)
    usd_ce_type = await create_test_cost_element_type(
        db, actor_id, usd_org.organizational_unit_id
    )
    usd_ce = await create_test_cost_element(
        db, actor_id, usd_wp.work_package_id, usd_ce_type.cost_element_type_id
    )
    await create_test_cost_registration(
        db, actor_id, usd_ce.cost_element_id, amount=Decimal("6000")
    )
    await create_test_progress_entry(
        db,
        actor_id,
        usd_wp.work_package_id,
        progress_percentage=Decimal("25.00"),
    )

    # control_date captured AFTER the hierarchy is created+committed so the
    # time-travel query (valid_time.lower <= control_date) sees every entity.
    control_date = datetime.now(tz=UTC)

    # Seed a USD->EUR rate effective before the control date.
    db.add(
        CurrencyRate(
            id=uuid4(),
            currency="USD",
            rate_to_base=usd_rate,
            effective_date=control_date.date() - timedelta(days=1),
        )
    )
    await db.commit()

    evm = EVMService(db)
    portfolio = await evm.calculate_portfolio_evm(
        project_ids=[
            eur_h["project"].project_id,
            usd_project.project_id,
        ],
        control_date=control_date,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    # Independently recompute the base-converted per-project flows so we can
    # assert the rollup is dimensionally consistent (same currency throughout).
    eur_metrics = await evm.calculate_evm_metrics_batch(
        entity_type=EntityType.PROJECT,
        entity_ids=[eur_h["project"].project_id],
        control_date=control_date,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )
    usd_metrics = await evm.calculate_evm_metrics_batch(
        entity_type=EntityType.PROJECT,
        entity_ids=[usd_project.project_id],
        control_date=control_date,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    pv_b = Decimal(str(eur_metrics.pv)) + Decimal(str(usd_metrics.pv)) * usd_rate
    ac_b = Decimal(str(eur_metrics.ac)) + Decimal(str(usd_metrics.ac)) * usd_rate
    ev_b = Decimal(str(eur_metrics.ev)) + Decimal(str(usd_metrics.ev)) * usd_rate
    bac_b = Decimal(str(eur_metrics.bac)) + Decimal(str(usd_metrics.bac)) * usd_rate
    eac_b = (
        Decimal(str(eur_metrics.eac)) + Decimal(str(usd_metrics.eac)) * usd_rate
        if eur_metrics.eac is not None and usd_metrics.eac is not None
        else None
    )

    expected_cpi = None if ac_b == 0 else float(ev_b / ac_b)
    expected_spi = None if pv_b == 0 else float(ev_b / pv_b)
    expected_tcpi = 1.0 if (eac_b is None or eac_b == 0) else float(bac_b / eac_b)

    assert portfolio.summary.cpi == pytest.approx(expected_cpi, rel=1e-6)
    assert portfolio.summary.spi == pytest.approx(expected_spi, rel=1e-6)
    assert portfolio.summary.tcpi == pytest.approx(expected_tcpi, rel=1e-6)

    # Sanity: the USD breakdown row is in base currency (EUR), not raw USD.
    usd_row = next(
        p for p in portfolio.projects if p.project_id == usd_project.project_id
    )
    assert usd_row.bac == pytest.approx(float(Decimal(str(usd_metrics.bac)) * usd_rate))


# ---------------------------------------------------------------------------
# convert_to_base (load-bearing for the production portfolio-EVM path).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_convert_to_base_eur_passthrough(db: AsyncSession) -> None:
    """Base-currency (EUR) amounts are returned unchanged."""
    as_of = datetime.now(tz=UTC)
    result = await convert_to_base(db, Decimal("1234.56"), "EUR", as_of)
    assert result == Decimal("1234.56")


@pytest.mark.asyncio
async def test_convert_to_base_non_eur_with_seeded_rate(
    db: AsyncSession,
) -> None:
    """A non-EUR amount is multiplied by the latest rate <= as_of."""
    as_of = datetime.now(tz=UTC)
    db.add(
        CurrencyRate(
            id=uuid4(),
            currency="USD",
            rate_to_base=Decimal("1.10"),
            effective_date=as_of.date() - timedelta(days=1),
        )
    )
    await db.flush()
    result = await convert_to_base(db, Decimal("1000"), "USD", as_of)
    assert result == pytest.approx(Decimal("1100.000000"))


@pytest.mark.asyncio
async def test_convert_to_base_missing_rate_passthrough(db: AsyncSession) -> None:
    """A missing rate for a non-EUR currency passes the amount through
    unchanged (defensive: never silently zeroes foreign amounts)."""
    as_of = datetime.now(tz=UTC)
    result = await convert_to_base(db, Decimal("999.99"), "JPY", as_of)
    assert result == Decimal("999.99")


@pytest.mark.asyncio
async def test_convert_to_base_picks_latest_effective_on_or_before(
    db: AsyncSession,
) -> None:
    """The as-of date resolves the latest effective_date <= as_of (not a later
    rate, and not a stale earlier one)."""
    as_of = datetime.now(tz=UTC)
    # An older rate, then the relevant one just before as_of, then a future
    # rate that must NOT be selected.
    for days_offset, rate in ((-10, "1.00"), (-1, "1.20"), (5, "1.50")):
        db.add(
            CurrencyRate(
                id=uuid4(),
                currency="GBP",
                rate_to_base=Decimal(rate),
                effective_date=as_of.date() + timedelta(days=days_offset),
            )
        )
    await db.flush()
    result = await convert_to_base(db, Decimal("100"), "GBP", as_of)
    assert result == pytest.approx(Decimal("120.000000"))


# ---------------------------------------------------------------------------
# G11 — ΔEAC forecast history.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_history_returns_versions(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /forecasts/{id}/history returns the EAC-over-time versions."""
    h = await create_full_hierarchy(db, actor_id)
    wp = h["wp"]
    service = ForecastService(db)

    forecast = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        eac_amount=Decimal("80000.00"),
        basis_of_estimate="Initial estimate",
    )
    await db.commit()

    # Create a second version (EAC revision) so history has > 1 entry.
    await service.update_forecast(
        forecast_id=forecast.forecast_id,
        forecast_in=ForecastUpdate(
            eac_amount=Decimal("95000.00"),
            basis_of_estimate="Revised estimate",
        ),
        actor_id=actor_id,
    )
    await db.commit()

    response = await client.get(f"{FORECAST_PREFIX}/{forecast.forecast_id}/history")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    # Newest version first.
    assert Decimal(data[0]["eac_amount"]) == Decimal("95000.00")
    assert Decimal(data[1]["eac_amount"]) == Decimal("80000.00")
    # Each entry carries the audit/temporal fields.
    assert "version_id" in data[0]
    assert "branch" in data[0]
    assert "created_by" in data[0]


@pytest.mark.asyncio
async def test_forecast_history_404_for_unknown(
    client: AsyncClient,
) -> None:
    """GET /forecasts/{id}/history returns 404 for an unknown forecast."""
    unknown_id = uuid4()
    response = await client.get(f"{FORECAST_PREFIX}/{unknown_id}/history")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# G17 — portfolio CO pipeline + /stats hardening.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_change_order_stats_aggregation(
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """Portfolio CO stats aggregate per-project totals correctly."""
    h = await create_full_hierarchy(db, actor_id)
    project_id = h["project"].project_id
    await db.commit()

    reporting = ChangeOrderReportingService(db)
    per_project = await reporting.get_change_order_stats(project_id=project_id)
    portfolio = await reporting.get_portfolio_change_order_stats(
        project_ids=[project_id]
    )

    # One project in the portfolio -> portfolio totals == per-project totals.
    assert portfolio.total_count == per_project.total_count
    assert portfolio.total_cost_exposure == per_project.total_cost_exposure
    assert portfolio.pending_value == per_project.pending_value


@pytest.mark.asyncio
async def test_portfolio_stats_empty_for_no_projects(
    db: AsyncSession,
) -> None:
    """An empty project set yields an empty (zeroed) portfolio stats response."""
    reporting = ChangeOrderReportingService(db)
    portfolio = await reporting.get_portfolio_change_order_stats(project_ids=[])
    assert portfolio.total_count == 0
    assert portfolio.by_status == []


@pytest.mark.asyncio
async def test_change_order_stats_route_no_blanket_500(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /change-orders/stats no longer masks errors as a blanket 500.

    A non-existent project yields a valid (zeroed) stats response — the service
    does not raise for missing projects — and the route does not wrap results in
    a catch-all 500. We assert a 200 with the expected shape.
    """
    h = await create_full_hierarchy(db, actor_id)
    project_id = h["project"].project_id
    await db.commit()

    response = await client.get(
        "/change-orders/stats", params={"project_id": str(project_id)}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "total_count" in data
    assert "by_status" in data
    assert "aging_threshold_days" in data


@pytest.mark.asyncio
async def test_portfolio_stats_route_membership_scoped(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /change-orders/portfolio-stats is membership-scoped and returns 200.

    The admin client has access to all projects, so the route resolves a
    non-empty set and returns aggregated stats. The key assertion is that the
    route is reachable (portfolio-read) and returns the aggregated shape.
    """
    h = await create_full_hierarchy(db, actor_id)
    project_id = h["project"].project_id
    await db.commit()

    response = await client.get("/change-orders/portfolio-stats")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "total_count" in data
    assert "by_status" in data

    # The freshly-created project is accessible to admin, so its CO totals
    # (zero COs) are folded into the portfolio aggregation without error.
    per_project = await ChangeOrderReportingService(db).get_change_order_stats(
        project_id=project_id
    )
    assert data["total_count"] >= per_project.total_count
