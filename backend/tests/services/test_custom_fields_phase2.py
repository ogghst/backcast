"""Phase 2 queryability battery for admin-defined custom fields.

Exercises the filtering, sorting, and global-search paths introduced in Phase 2
of the custom-fields initiative (memory note 44). Custom-field values live in a
``custom_fields`` JSONB dict on the entity row; queryability is gated by the
``searchable`` flag (UI) and ``ai_visible`` flag (AI) on the bound
``CustomEntityTemplate``'s ``field_definitions``.

Coverage (per the implementation spec):
  (a) GET /projects?filters=<searchable_code>:<value> matches the subset.
  (b) Filter on a NON-searchable custom field -> rejected (400).
  (c) Sort by a numeric custom key asc/desc with NULLs last.
  (d) Global search matches a row via a searchable custom field (UI mode);
      a searchable=false field is NOT matched.
  (e) AI search mode matches an ai_visible=true field; ai_visible=false is NOT.
  (f) Key-collision: a custom field named ``code`` does NOT shadow the real
      ``code`` column.
  (g) Global-search result objects do NOT leak custom_fields values.

SELF-CLEANUP: the ``db`` fixture COMMITS at teardown (conftest.py line 100-101)
so every persistent row created here MUST be removed via an
``async_session_maker()`` session in a ``finally`` block (memory note 35).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.domain.custom_entity_template import CustomEntityTemplate
from app.services.global_search_service import GlobalSearchService
from tests.conftest import TEST_USER_ID
from tests.factories import create_test_project

# ---------------------------------------------------------------------------
# Self-cleanup helpers (memory note 35: db fixture COMMITS at teardown).
# ---------------------------------------------------------------------------


async def _cleanup_by_root_ids(table: str, root_col: str, ids: set[UUID]) -> None:
    """Delete every row in *table* whose *root_col* is in *ids*."""
    if not ids:
        return
    async with async_session_maker() as s:
        await s.execute(
            text(f"DELETE FROM {table} WHERE {root_col} = ANY(:ids)"),
            {"ids": list(ids)},
        )
        await s.commit()


async def _cleanup_templates(root_ids: set[UUID]) -> None:
    if not root_ids:
        return
    async with async_session_maker() as s:
        await s.execute(
            text(
                "DELETE FROM custom_entity_templates "
                "WHERE custom_entity_template_id = ANY(:ids)"
            ),
            {"ids": list(root_ids)},
        )
        await s.commit()


async def _seed_template(
    db: AsyncSession,
    *,
    target_entity_type: str,
    field_definitions: dict[str, Any],
    actor_id: UUID,
) -> UUID:
    """Insert a CURRENT CustomEntityTemplate row and return its root id."""
    root_id = uuid4()
    db.add(
        CustomEntityTemplate(
            custom_entity_template_id=root_id,
            organizational_unit_id=uuid4(),
            target_entity_type=target_entity_type,
            code=f"TPL-{root_id.hex[:6].upper()}",
            name=f"Phase2 template {root_id.hex[:6]}",
            field_definitions=field_definitions,
            created_by=actor_id,
        )
    )
    await db.commit()
    return root_id


# ===========================================================================
# (a) + (b) + (f) FILTERING via GET /projects?filters=...
# ===========================================================================


class TestProjectCustomFieldFiltering:
    """GET /projects?filters=<code>:<value> with custom-field support."""

    @pytest.mark.asyncio
    async def test_searchable_custom_field_filters_subset(
        self, db: AsyncSession, client: AsyncClient, actor_id: UUID
    ) -> None:
        """A searchable select field filters the project list to matches.

        Seeds a PROJECT template with a ``region`` select field marked
        ``searchable: true``, creates three projects (two EU, one US, one with
        no custom_fields), and asserts ``?filters=region:EU`` returns only the
        two EU projects.
        """
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "region": {
                    "type": "select",
                    "label": "Region",
                    "options": ["EU", "US", "APAC"],
                    "searchable": True,
                }
            },
            actor_id=actor_id,
        )
        p_eu1 = await create_test_project(
            db, actor_id, name="P-EU-1", custom_fields={"region": "EU"}
        )
        p_eu2 = await create_test_project(
            db, actor_id, name="P-EU-2", custom_fields={"region": "EU"}
        )
        p_us = await create_test_project(
            db, actor_id, name="P-US", custom_fields={"region": "US"}
        )
        p_none = await create_test_project(db, actor_id, name="P-NONE")
        await db.commit()
        project_ids = {
            p_eu1.project_id,
            p_eu2.project_id,
            p_us.project_id,
            p_none.project_id,
        }

        try:
            resp = await client.get(
                "/projects", params={"filters": "region:EU", "per_page": 100}
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            codes = {item["code"] for item in data["items"]}
            eu_codes = {p_eu1.code, p_eu2.code}
            assert codes == eu_codes, (
                f"expected only EU projects {eu_codes}, got {codes}"
            )
        finally:
            await _cleanup_by_root_ids("projects", "project_id", project_ids)
            await _cleanup_templates({template_root})

    @pytest.mark.asyncio
    async def test_non_searchable_custom_field_rejected(
        self, db: AsyncSession, client: AsyncClient, actor_id: UUID
    ) -> None:
        """A NON-searchable custom field must NOT be filterable (400).

        Seeds a ``secret`` text field with ``searchable`` absent (defaults
        False). Filtering on it is rejected with HTTP 400 rather than silently
        matching.
        """
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={"secret": {"type": "text", "label": "Secret"}},
            actor_id=actor_id,
        )
        p = await create_test_project(
            db, actor_id, name="P-SECRET", custom_fields={"secret": "classified"}
        )
        await db.commit()

        try:
            resp = await client.get(
                "/projects", params={"filters": "secret:classified"}
            )
            assert resp.status_code == 400, resp.text
        finally:
            await _cleanup_by_root_ids("projects", "project_id", {p.project_id})
            await _cleanup_templates({template_root})

    @pytest.mark.asyncio
    async def test_custom_field_named_code_does_not_shadow_real_column(
        self, db: AsyncSession, client: AsyncClient, actor_id: UUID
    ) -> None:
        """A custom field literally named ``code`` must NOT shadow the real
        ``code`` column (key-collision guard).

        ``?filters=code:<real_code>`` filters on the REAL projects.code column,
        not the custom ``code`` JSONB key.
        """
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "code": {
                    "type": "text",
                    "label": "Custom code",
                    "searchable": True,
                }
            },
            actor_id=actor_id,
        )
        p1 = await create_test_project(
            db, actor_id, name="COLLIDE-1", custom_fields={"code": "ZZ-CUSTOM"}
        )
        p2 = await create_test_project(db, actor_id, name="COLLIDE-2")
        await db.commit()

        try:
            # Filter on the REAL code column value of p1.
            resp = await client.get("/projects", params={"filters": f"code:{p1.code}"})
            assert resp.status_code == 200, resp.text
            codes = {item["code"] for item in resp.json()["items"]}
            assert codes == {p1.code}, (
                f"real-column filter leaked: expected {{{p1.code}}}, got {codes}"
            )
        finally:
            await _cleanup_by_root_ids(
                "projects", "project_id", {p1.project_id, p2.project_id}
            )
            await _cleanup_templates({template_root})

    @pytest.mark.asyncio
    async def test_multi_value_in_filter_select_and_number(
        self, db: AsyncSession, client: AsyncClient, actor_id: UUID
    ) -> None:
        """A comma-separated ``filters=code:v1,v2`` IN clause works for both
        select- and number-typed custom fields (per-value cast).

        Seeds region (select) values EU/US/APAC + a row with no custom_fields,
        plus a priority_score (number) field. ``region:EU,US`` returns exactly
        the EU+US rows; ``priority_score:9,100`` returns both numeric rows and
        excludes a non-listed numeric value (covers per-value NUMERIC casting
        in the IN branch).
        """
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "region": {
                    "type": "select",
                    "label": "Region",
                    "options": ["EU", "US", "APAC"],
                    "searchable": True,
                },
                "priority_score": {
                    "type": "number",
                    "label": "Priority",
                    "searchable": True,
                },
            },
            actor_id=actor_id,
        )
        p_eu = await create_test_project(
            db,
            actor_id,
            name="IN-EU",
            custom_fields={"region": "EU", "priority_score": 9},
        )
        p_us = await create_test_project(
            db,
            actor_id,
            name="IN-US",
            custom_fields={"region": "US", "priority_score": 100},
        )
        p_apac = await create_test_project(
            db,
            actor_id,
            name="IN-APAC",
            custom_fields={"region": "APAC", "priority_score": 10},
        )
        p_none = await create_test_project(db, actor_id, name="IN-NONE")
        await db.commit()
        project_ids = {
            p_eu.project_id,
            p_us.project_id,
            p_apac.project_id,
            p_none.project_id,
        }

        try:
            # select IN: EU,US — APAC and the empty row are excluded.
            resp = await client.get(
                "/projects", params={"filters": "region:EU,US", "per_page": 100}
            )
            assert resp.status_code == 200, resp.text
            codes = {item["code"] for item in resp.json()["items"]}
            assert codes == {p_eu.code, p_us.code}, (
                f"select IN filter wrong: expected EU+US, got {codes}"
            )

            # number IN: 9,100 — the 10 row is excluded (per-value NUMERIC cast).
            resp = await client.get(
                "/projects",
                params={"filters": "priority_score:9,100", "per_page": 100},
            )
            assert resp.status_code == 200, resp.text
            codes = {item["code"] for item in resp.json()["items"]}
            assert codes == {p_eu.code, p_us.code}, (
                f"number IN filter wrong: expected score 9+100, got {codes}"
            )
        finally:
            await _cleanup_by_root_ids("projects", "project_id", project_ids)
            await _cleanup_templates({template_root})

    @pytest.mark.asyncio
    async def test_cross_template_union_filter(
        self, db: AsyncSession, client: AsyncClient, actor_id: UUID
    ) -> None:
        """Filtering resolves codes per ``target_entity_type`` (union across
        templates), NOT per-row-template.

        Seeds TWO PROJECT templates: A defines searchable ``region``; B defines
        a different searchable field (``owner``). p_a is bound to A and stores
        region:EU via the service chokepoint; p_b is bound to B and stores
        region:EU via a RAW INSERT (the write chokepoint would reject the key
        for B). ``?filters=region:EU`` must match BOTH — pinning the
        per-entity-type union design.
        """
        tpl_a = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "region": {
                    "type": "select",
                    "label": "Region",
                    "options": ["EU", "US"],
                    "searchable": True,
                }
            },
            actor_id=actor_id,
        )
        tpl_b = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "owner": {
                    "type": "text",
                    "label": "Owner",
                    "searchable": True,
                }
            },
            actor_id=actor_id,
        )
        # p_a: bound to A, region:EU stored via the chokepoint.
        p_a = await create_test_project(
            db,
            actor_id,
            name="XTPL-A",
            custom_entity_template_root_id=tpl_a,
            custom_fields={"region": "EU"},
        )
        await db.commit()

        # p_b: bound to B, region:EU stored via RAW INSERT (the chokepoint
        # rejects unknown keys for B; the read path must still find it).
        p_b = await create_test_project(
            db,
            actor_id,
            name="XTPL-B",
            custom_entity_template_root_id=tpl_b,
        )
        await db.commit()
        await db.refresh(p_b)
        await db.execute(
            text("UPDATE projects SET custom_fields = :cf WHERE id = :pid"),
            {"cf": json.dumps({"region": "EU"}), "pid": p_b.id},
        )
        await db.commit()

        project_ids = {p_a.project_id, p_b.project_id}

        try:
            resp = await client.get(
                "/projects", params={"filters": "region:EU", "per_page": 100}
            )
            assert resp.status_code == 200, resp.text
            codes = {item["code"] for item in resp.json()["items"]}
            assert codes == {p_a.code, p_b.code}, (
                f"cross-template union broken: expected both, got {codes}"
            )
        finally:
            await _cleanup_by_root_ids("projects", "project_id", project_ids)
            await _cleanup_templates({tpl_a, tpl_b})

    @pytest.mark.asyncio
    async def test_type_mismatch_does_not_500(
        self, db: AsyncSession, client: AsyncClient, actor_id: UUID
    ) -> None:
        """A stored value that cannot be cast to the (re)defined type yields
        NULL (excluded) — NOT a 500.

        Seeds a project with a ``text`` field storing "abc"; then redefines
        the template's field type as ``number`` (spec drift). The defensive
        regex guard makes the mismatched row yield NULL on the NUMERIC cast,
        so ``?filters=<key>:10`` returns 200 with no match instead of a 500.
        """
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "drift_field": {
                    "type": "text",
                    "label": "Drift",
                    "searchable": True,
                }
            },
            actor_id=actor_id,
        )
        p = await create_test_project(
            db,
            actor_id,
            name="DRIFT-PROJ",
            custom_entity_template_root_id=template_root,
            custom_fields={"drift_field": "abc"},
        )
        await db.commit()

        # Simulate spec drift: redefine the field type as number directly on
        # the template's current version. (Spec drift is an admin error case;
        # the read path must stay robust to it.)
        await db.execute(
            text(
                "UPDATE custom_entity_templates SET field_definitions = :fd "
                "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL "
                "AND custom_entity_template_id = :rid"
            ),
            {
                "fd": json.dumps(
                    {
                        "drift_field": {
                            "type": "number",
                            "label": "Drift",
                            "searchable": True,
                        }
                    }
                ),
                "rid": template_root,
            },
        )
        await db.commit()

        try:
            resp = await client.get(
                "/projects", params={"filters": "drift_field:10", "per_page": 100}
            )
            # The corrupt row yields NULL on the NUMERIC cast (defensive guard)
            # and is excluded — NOT a 500. Locks in FIX A.
            assert resp.status_code == 200, resp.text
            codes = {item["code"] for item in resp.json()["items"]}
            assert p.code not in codes, f"corrupt row should be excluded, got {codes}"
        finally:
            await _cleanup_by_root_ids("projects", "project_id", {p.project_id})
            await _cleanup_templates({template_root})


# ===========================================================================
# (c) SORTING by a numeric custom key
# ===========================================================================


class TestProjectCustomFieldSorting:
    """Sort the project list by a numeric custom-field key (NULLs last)."""

    @pytest.mark.asyncio
    async def test_sort_by_numeric_custom_field_asc_nulls_last(
        self, db: AsyncSession, client: AsyncClient, actor_id: UUID
    ) -> None:
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "priority_score": {
                    "type": "number",
                    "label": "Priority",
                    "searchable": True,
                }
            },
            actor_id=actor_id,
        )
        p_low = await create_test_project(
            db, actor_id, name="S-LOW", custom_fields={"priority_score": 9}
        )
        p_mid = await create_test_project(
            db, actor_id, name="S-MID", custom_fields={"priority_score": 10}
        )
        p_high = await create_test_project(
            db, actor_id, name="S-HIGH", custom_fields={"priority_score": 100}
        )
        p_null = await create_test_project(db, actor_id, name="S-NULL")
        await db.commit()
        project_ids = {
            p_low.project_id,
            p_mid.project_id,
            p_high.project_id,
            p_null.project_id,
        }

        try:
            # Ascending: 9, 10, 100, NULL (numeric). Values chosen so lexical
            # order ("10","100","9") diverges from numeric (9,10,100) — this
            # makes the NUMERIC cast load-bearing.
            resp = await client.get(
                "/projects",
                params={
                    "filters": f"code:{p_low.code},{p_mid.code},{p_high.code},{p_null.code}",
                    "sort_field": "priority_score",
                    "sort_order": "asc",
                    "per_page": 100,
                },
            )
            assert resp.status_code == 200, resp.text
            names = [item["name"] for item in resp.json()["items"]]
            assert names == ["S-LOW", "S-MID", "S-HIGH", "S-NULL"], names

            # Descending: 100, 10, 9, NULL (NULLs still last).
            resp = await client.get(
                "/projects",
                params={
                    "filters": f"code:{p_low.code},{p_mid.code},{p_high.code},{p_null.code}",
                    "sort_field": "priority_score",
                    "sort_order": "desc",
                    "per_page": 100,
                },
            )
            assert resp.status_code == 200, resp.text
            names = [item["name"] for item in resp.json()["items"]]
            assert names == ["S-HIGH", "S-MID", "S-LOW", "S-NULL"], names
        finally:
            await _cleanup_by_root_ids("projects", "project_id", project_ids)
            await _cleanup_templates({template_root})

    @pytest.mark.asyncio
    async def test_sort_by_date_custom_field_nulls_last(
        self, db: AsyncSession, client: AsyncClient, actor_id: UUID
    ) -> None:
        """Sort by a ``date``-type custom key asc/desc with NULLs last.

        Seeds three ISO-8601 dates spanning different years/months plus a null
        row; asc -> chronological with null last; desc -> reverse-chronological
        with null last. Exercises the TIMESTAMP-cast branch + nullslast on a
        non-numeric key.
        """
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "due_date": {
                    "type": "date",
                    "label": "Due",
                    "searchable": True,
                }
            },
            actor_id=actor_id,
        )
        p_early = await create_test_project(
            db,
            actor_id,
            name="D-EARLY",
            custom_fields={"due_date": "2023-01-15"},
        )
        p_mid = await create_test_project(
            db,
            actor_id,
            name="D-MID",
            custom_fields={"due_date": "2024-06-01"},
        )
        p_late = await create_test_project(
            db,
            actor_id,
            name="D-LATE",
            custom_fields={"due_date": "2025-12-10"},
        )
        p_null = await create_test_project(db, actor_id, name="D-NULL")
        await db.commit()
        project_ids = {
            p_early.project_id,
            p_mid.project_id,
            p_late.project_id,
            p_null.project_id,
        }

        try:
            # Ascending: chronological, NULL last.
            resp = await client.get(
                "/projects",
                params={
                    "filters": f"code:{p_early.code},{p_mid.code},{p_late.code},{p_null.code}",
                    "sort_field": "due_date",
                    "sort_order": "asc",
                    "per_page": 100,
                },
            )
            assert resp.status_code == 200, resp.text
            names = [item["name"] for item in resp.json()["items"]]
            assert names == ["D-EARLY", "D-MID", "D-LATE", "D-NULL"], names

            # Descending: reverse-chronological, NULL still last.
            resp = await client.get(
                "/projects",
                params={
                    "filters": f"code:{p_early.code},{p_mid.code},{p_late.code},{p_null.code}",
                    "sort_field": "due_date",
                    "sort_order": "desc",
                    "per_page": 100,
                },
            )
            assert resp.status_code == 200, resp.text
            names = [item["name"] for item in resp.json()["items"]]
            assert names == ["D-LATE", "D-MID", "D-EARLY", "D-NULL"], names
        finally:
            await _cleanup_by_root_ids("projects", "project_id", project_ids)
            await _cleanup_templates({template_root})


# ===========================================================================
# (d) + (e) + (g) GLOBAL SEARCH — searchable / ai_visible / no-leak
# ===========================================================================


class TestGlobalSearchCustomFields:
    """Global search matches via custom fields, gated by searchable/ai_visible."""

    @pytest.mark.asyncio
    async def test_ui_search_matches_searchable_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """UI-mode search matches a project via a searchable custom field; a
        searchable=False field is NOT matched."""
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "ticket_ref": {
                    "type": "text",
                    "label": "Ticket",
                    "searchable": True,
                },
                "internal_note": {
                    "type": "text",
                    "label": "Internal",
                    # searchable absent -> False; but ai_visible True so the AI
                    # test below can reuse the template.
                    "ai_visible": True,
                },
            },
            actor_id=actor_id,
        )
        # The project's standard fields do NOT contain "JIRA-9999".
        p = await create_test_project(
            db,
            actor_id,
            name="SEARCHABLE-PROJ",
            custom_fields={
                "ticket_ref": "JIRA-9999",
                "internal_note": "JIRA-9999-secret",
            },
        )
        await db.commit()

        service = GlobalSearchService(db)
        try:
            # UI mode: ticket_ref (searchable) matches.
            resp = await service.search(
                "JIRA-9999",
                user_id=TEST_USER_ID,
                search_mode="ui",
            )
            matched_ids = {
                str(r.root_id) for r in resp.results if r.entity_type == "project"
            }
            assert str(p.project_id) in matched_ids, (
                f"searchable field did not match; results={resp.results}"
            )

            # internal_note is NOT searchable -> a query unique to it must NOT
            # match via the custom-field path. Use the "-secret" suffix which
            # only appears in internal_note.
            resp2 = await service.search(
                "JIRA-9999-secret",
                user_id=TEST_USER_ID,
                search_mode="ui",
            )
            matched2 = {
                str(r.root_id) for r in resp2.results if r.entity_type == "project"
            }
            assert str(p.project_id) not in matched2, (
                f"non-searchable field leaked into UI search; results={resp2.results}"
            )
        finally:
            await _cleanup_by_root_ids("projects", "project_id", {p.project_id})
            await _cleanup_templates({template_root})

    @pytest.mark.asyncio
    async def test_ai_search_matches_ai_visible_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """AI-mode search matches a project via an ai_visible custom field; an
        ai_visible=False field is NOT matched (D8: never reaches the LLM)."""
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "ai_summary": {
                    "type": "text",
                    "label": "AI summary",
                    "ai_visible": True,
                },
                "confidential": {
                    "type": "text",
                    "label": "Confidential",
                    # ai_visible absent -> False.
                },
            },
            actor_id=actor_id,
        )
        p = await create_test_project(
            db,
            actor_id,
            name="AI-VIS-PROJ",
            custom_fields={
                "ai_summary": "PLAN-ALPHA-OVERVIEW",
                "confidential": "PLAN-ALPHA-SECRET",
            },
        )
        await db.commit()

        service = GlobalSearchService(db)
        try:
            # AI mode: ai_summary matches.
            resp = await service.search(
                "PLAN-ALPHA-OVERVIEW",
                user_id=TEST_USER_ID,
                search_mode="ai",
            )
            matched = {
                str(r.root_id) for r in resp.results if r.entity_type == "project"
            }
            assert str(p.project_id) in matched, resp.results

            # confidential is NOT ai_visible -> must not match in AI mode.
            resp2 = await service.search(
                "PLAN-ALPHA-SECRET",
                user_id=TEST_USER_ID,
                search_mode="ai",
            )
            matched2 = {
                str(r.root_id) for r in resp2.results if r.entity_type == "project"
            }
            assert str(p.project_id) not in matched2, (
                f"non-ai_visible field leaked into AI search; results={resp2.results}"
            )
        finally:
            await _cleanup_by_root_ids("projects", "project_id", {p.project_id})
            await _cleanup_templates({template_root})

    @pytest.mark.asyncio
    async def test_search_results_do_not_leak_custom_field_values(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """Search result objects surface standard fields ONLY — custom_fields
        values (even when matched) never appear in the serialized result."""
        secret_token = "LEAKGUARD-TOKEN-XYZ"
        template_root = await _seed_template(
            db,
            target_entity_type="PROJECT",
            field_definitions={
                "api_key": {
                    "type": "text",
                    "label": "API key",
                    "searchable": True,
                    "ai_visible": True,
                }
            },
            actor_id=actor_id,
        )
        p = await create_test_project(
            db,
            actor_id,
            name="LEAK-PROJ",
            custom_fields={"api_key": secret_token},
        )
        await db.commit()

        service = GlobalSearchService(db)
        try:
            for mode in ("ui", "ai"):
                resp = await service.search(
                    secret_token,
                    user_id=TEST_USER_ID,
                    search_mode=mode,  # type: ignore[arg-type]
                )
                # Must match (the field is both searchable and ai_visible).
                assert any(
                    str(r.root_id) == str(p.project_id) and r.entity_type == "project"
                    for r in resp.results
                ), f"{mode} mode did not match; results={resp.results}"

                # The RESULTS array must NOT carry the secret token — neither
                # a custom_fields key nor a snippet. (The top-level ``query``
                # field legitimately echoes the user's own search term, so we
                # serialize the results list only, not the whole response.)
                results_json = json.dumps(
                    [r.model_dump(mode="json") for r in resp.results]
                )
                assert secret_token not in results_json, (
                    f"custom-field value leaked into {mode} search results: "
                    f"{results_json}"
                )
        finally:
            await _cleanup_by_root_ids("projects", "project_id", {p.project_id})
            await _cleanup_templates({template_root})
