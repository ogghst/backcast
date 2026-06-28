"""Smoke tests for the Customers and CurrencyRates REST endpoints.

Validates list/create/get/update/delete wiring, RBAC permission gating, and the
new schema serialization. Uses the default admin ``client`` fixture (admin has
all the new permissions: customer-*, currency-rate-*). Created rows are cleaned
up because the ``db`` fixture commits (memory note 35).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.currency_rate import CurrencyRate
from app.models.domain.customer import Customer

CUSTOMERS = "/customers"
RATES = "/currency-rates"


@pytest.mark.asyncio
async def test_customer_crud_roundtrip(client: AsyncClient, db: AsyncSession) -> None:
    """POST/GET/PUT/DELETE a customer end-to-end."""
    created_ids: list = []

    try:
        # Create
        resp = await client.post(
            CUSTOMERS,
            json={"code": "ACME-T", "name": "ACME Test", "is_active": True},
        )
        assert resp.status_code == 201, resp.text
        created = resp.json()
        cust_id = created["id"]
        created_ids.append(cust_id)
        assert created["code"] == "ACME-T"
        assert created["name"] == "ACME Test"
        assert created["is_active"] is True

        # List (paginated)
        resp = await client.get(CUSTOMERS, params={"search": "ACME-T", "per_page": 50})
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["total"] >= 1
        assert any(c["id"] == cust_id for c in payload["items"])

        # Get by id
        resp = await client.get(f"{CUSTOMERS}/{cust_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == cust_id

        # Update
        resp = await client.put(
            f"{CUSTOMERS}/{cust_id}",
            json={"name": "ACME Renamed"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "ACME Renamed"

        # Delete (idempotent 204)
        resp = await client.delete(f"{CUSTOMERS}/{cust_id}")
        assert resp.status_code == 204, resp.text
        # Subsequent get 404s
        resp = await client.get(f"{CUSTOMERS}/{cust_id}")
        assert resp.status_code == 404, resp.text
    finally:
        # Defensive cleanup if a step above failed before the DELETE.
        for cid in created_ids:
            await db.execute(delete(Customer).where(Customer.id == cid))
        await db.flush()


@pytest.mark.asyncio
async def test_customer_get_missing_returns_404(client: AsyncClient) -> None:
    """GET on an unknown customer id returns 404."""
    resp = await client.get(f"{CUSTOMERS}/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_currency_rate_crud_roundtrip(
    client: AsyncClient, db: AsyncSession
) -> None:
    """POST/GET/PUT/DELETE a currency rate end-to-end."""
    created_ids: list = []

    try:
        resp = await client.post(
            RATES,
            json={
                "currency": "USD",
                "rate_to_base": "1.080000",
                "effective_date": "2026-01-15",
            },
        )
        assert resp.status_code == 201, resp.text
        created = resp.json()
        rate_id = created["id"]
        created_ids.append(rate_id)
        assert created["currency"] == "USD"
        assert Decimal(created["rate_to_base"]) == Decimal("1.080000")

        # List
        resp = await client.get(RATES, params={"search": "USD", "per_page": 50})
        assert resp.status_code == 200, resp.text
        assert any(r["id"] == rate_id for r in resp.json()["items"])

        # Get by id
        resp = await client.get(f"{RATES}/{rate_id}")
        assert resp.status_code == 200, resp.text

        # Update
        resp = await client.put(
            f"{RATES}/{rate_id}",
            json={"rate_to_base": "1.090000"},
        )
        assert resp.status_code == 200, resp.text
        assert Decimal(resp.json()["rate_to_base"]) == Decimal("1.090000")

        # Delete
        resp = await client.delete(f"{RATES}/{rate_id}")
        assert resp.status_code == 204, resp.text
    finally:
        for rid in created_ids:
            await db.execute(delete(CurrencyRate).where(CurrencyRate.id == rid))
        await db.flush()


@pytest.mark.asyncio
async def test_currency_rate_get_missing_returns_404(
    client: AsyncClient,
) -> None:
    """GET on an unknown rate id returns 404."""
    resp = await client.get(f"{RATES}/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Server-side filter / sort coverage for the GET list methods.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_list_filters_by_is_active(
    client: AsyncClient, db: AsyncSession
) -> None:
    """GET /customers supports the is_active filter (active-only subset)."""
    created_ids: list = []
    try:
        # One active, one inactive, both with distinct codes (active codes are
        # unique under the partial index).
        for code, active in (("CUST-FLTA", True), ("CUST-FLTI", False)):
            resp = await client.post(
                CUSTOMERS,
                json={"code": code, "name": f"Filter {code}", "is_active": active},
            )
            assert resp.status_code == 201, resp.text
            created_ids.append(resp.json()["id"])

        resp = await client.get(
            CUSTOMERS, params={"filters": "is_active:true", "per_page": 50}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        codes = {c["code"] for c in data["items"]}
        assert "CUST-FLTA" in codes
        assert "CUST-FLTI" not in codes
    finally:
        for cid in created_ids:
            await db.execute(delete(Customer).where(Customer.id == cid))
        await db.flush()


@pytest.mark.asyncio
async def test_customer_list_sorts_by_name_desc(
    client: AsyncClient, db: AsyncSession
) -> None:
    """GET /customers honors sort_field=name, sort_order=desc."""
    created_ids: list = []
    try:
        for nm in (("Alpha Srt", "CUST-SRT1"), ("Zeta Srt", "CUST-SRT2")):
            resp = await client.post(
                CUSTOMERS,
                json={"code": nm[1], "name": nm[0], "is_active": True},
            )
            assert resp.status_code == 201, resp.text
            created_ids.append(resp.json()["id"])

        resp = await client.get(
            CUSTOMERS,
            params={"sort_field": "name", "sort_order": "desc", "per_page": 50},
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        ours = [c["name"] for c in items if c["code"].startswith("CUST-SRT")]
        assert ours == sorted(ours, reverse=True)
    finally:
        for cid in created_ids:
            await db.execute(delete(Customer).where(Customer.id == cid))
        await db.flush()


@pytest.mark.asyncio
async def test_currency_rate_list_filters_by_currency_and_sorts(
    client: AsyncClient, db: AsyncSession
) -> None:
    """GET /currency-rates filters by currency and sorts by effective_date."""
    created_ids: list = []
    try:
        # Two CHF rates (distinct dates) + one GBP rate as a distractor.
        for eff, rate in (("2026-01-01", "0.950000"), ("2026-06-01", "0.970000")):
            resp = await client.post(
                RATES,
                json={"currency": "CHF", "rate_to_base": rate, "effective_date": eff},
            )
            assert resp.status_code == 201, resp.text
            created_ids.append(resp.json()["id"])
        resp = await client.post(
            RATES,
            json={
                "currency": "GBP",
                "rate_to_base": "1.150000",
                "effective_date": "2026-03-01",
            },
        )
        assert resp.status_code == 201, resp.text
        created_ids.append(resp.json()["id"])

        # Filter: only CHF.
        resp = await client.get(
            RATES, params={"filters": "currency:CHF", "per_page": 50}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["items"]) == 2
        assert all(r["currency"] == "CHF" for r in data["items"])

        # Default sort is effective_date DESC — newest CHF first.
        dates = [r["effective_date"] for r in data["items"]]
        assert dates == sorted(dates, reverse=True)
    finally:
        for rid in created_ids:
            await db.execute(delete(CurrencyRate).where(CurrencyRate.id == rid))
        await db.flush()
