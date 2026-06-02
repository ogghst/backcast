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
