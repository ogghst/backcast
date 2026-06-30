"""Tests for EVM (Earned Value Management) API routes.

Tests EVM metric calculation at work package, control account, WBS element,
and project levels.
"""

from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_full_hierarchy,
    create_test_cost_registration,
    create_test_progress_entry,
)

PREFIX = "/evm"
WP_PREFIX = "/work-packages"


@pytest.mark.asyncio
async def test_evm_work_package_level(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /work-packages/{wp_id}/evm returns BAC/PV/AC/EV/CPI/SPI."""
    h = await create_full_hierarchy(db, actor_id)
    # Add actual cost
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("10000")
    )
    # Add progress
    await create_test_progress_entry(
        db, actor_id, h["wp"].work_package_id, progress_percentage=Decimal("50.00")
    )
    await db.commit()

    response = await client.get(f"{WP_PREFIX}/{h['wp'].work_package_id}/evm")
    assert response.status_code == 200, response.text
    data = response.json()
    # Verify core EVM metrics are present
    assert "bac" in data
    assert "pv" in data
    assert "ac" in data
    assert "ev" in data
    assert "cv" in data
    assert "sv" in data


@pytest.mark.asyncio
async def test_evm_project_level(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /evm/project/{id}/metrics returns aggregated project EVM."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("5000")
    )
    await db.commit()

    response = await client.get(f"{PREFIX}/project/{h['project'].project_id}/metrics")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "bac" in data
    assert "ac" in data
    assert data["entity_type"] == "project"


@pytest.mark.asyncio
async def test_evm_wbs_element_level(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /evm/wbs_element/{id}/metrics returns aggregated WBS EVM."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(
        db, actor_id, h["ce"].cost_element_id, amount=Decimal("5000")
    )
    await db.commit()

    response = await client.get(
        f"{PREFIX}/wbs_element/{h['wbs'].wbs_element_id}/metrics"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "bac" in data
    assert data["entity_type"] == "wbs_element"


@pytest.mark.asyncio
async def test_evm_project_control_date_before_first_version_returns_200(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """F3: control_date before the project's first valid_time returns 200.

    The project exists but has no version valid as of the past control_date.
    Previously this raised ValueError -> HTTP 404 (error storm). It must now
    return 200 with zeroed metrics and a non-empty warning.
    """
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # control_date well before the project version's valid_time lower bound.
    response = await client.get(
        f"{PREFIX}/project/{h['project'].project_id}/metrics"
        "?control_date=2020-01-01T00:00:00Z"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["entity_type"] == "project"
    assert float(data["bac"]) == 0.0
    assert float(data["ac"]) == 0.0
    assert float(data["ev"]) == 0.0
    assert data["cpi"] is None
    assert data["spi"] is None
    assert data["warning"] is not None
    assert "2020-01-01" in data["warning"]
