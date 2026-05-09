"""Change Order Lifecycle Simulation v2 — Full Realistic Scenario."""

import json
from datetime import UTC, datetime

import httpx

BASE = "http://localhost:8020/api/v1"
TIMEOUT = 30.0

USERS = {
    "admin": {"email": "admin@backcast.org", "password": "adminadmin"},
    "pm": {"email": "pm@backcast.org", "password": "backcast"},
    "eng_lead": {"email": "eng.lead@backcast.org", "password": "backcast"},
    "const_super": {"email": "const.super@backcast.org", "password": "backcast"},
    "viewer": {"email": "viewer@backcast.org", "password": "backcast"},
}

tokens: dict[str, str] = {}
results: list[dict] = []
entities: dict[str, str] = {}


def log(category: str, test: str, status: str, detail: str = "") -> None:
    results.append(
        {"category": category, "test": test, "status": status, "detail": detail}
    )
    icon = {"PASS": "✓", "FAIL": "✗", "WARN": "!", "INFO": "i", "BUG": "🐛"}.get(
        status, "?"
    )
    print(f"  [{icon}] {status}: {test}" + (f" — {detail}" if detail else ""))


def h(user: str) -> dict:
    return {
        "Authorization": f"Bearer {tokens[user]}",
        "Content-Type": "application/json",
    }


async def call(
    c: httpx.AsyncClient,
    method: str,
    url: str,
    user: str,
    json_data: dict | None = None,
    params: dict | None = None,
) -> httpx.Response:
    return await c.request(
        method, f"{BASE}{url}", headers=h(user), json=json_data, params=params
    )


def extract_data(resp_json):
    """Extract data from paginated or direct response."""
    if isinstance(resp_json, dict):
        # Try common pagination keys
        for key in ("data", "items"):
            if key in resp_json:
                return resp_json[key]
        return resp_json
    return resp_json


async def run_simulation() -> None:
    print("\n" + "=" * 70)
    print("  CHANGE ORDER LIFECYCLE SIMULATION v2")
    print(f"  {datetime.now(UTC).isoformat()}")
    print("  Scenario: Paint Booth Modernization — Factory A")
    print("=" * 70)

    # ── PHASE 0: AUTH ──
    print("\n── PHASE 0: Authentication ──")
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
        for name, creds in USERS.items():
            r = await c.post(
                f"{BASE}/auth/login",
                data={"username": creds["email"], "password": creds["password"]},
            )
            if r.status_code == 200:
                tokens[name] = r.json()["access_token"]
                log("AUTH", f"Login {name}", "PASS")
            else:
                log("AUTH", f"Login {name}", "FAIL", r.text[:200])
                return

        # Get user IDs
        r_users = await call(c, "GET", "/users", "admin")
        users_list = extract_data(r_users.json()) if r_users.status_code == 200 else []
        for u in users_list if isinstance(users_list, list) else []:
            email = u.get("email", "")
            for key in USERS:
                if email == USERS[key]["email"]:
                    entities[f"uid_{key}"] = u["user_id"]
                    break

        # ── PHASE 1: PROJECT ──
        print("\n── PHASE 1: Project & Budget Setup ──")

        ts = datetime.now(UTC).strftime("%H%M%S")
        r = await call(
            c,
            "POST",
            "/projects",
            "admin",
            {
                "code": f"PRJ-PAINT-{ts}",
                "name": "Paint Booth Modernization — Factory A",
                "description": "Full upgrade of paint booth: ventilation, robotics, QA systems",
                "contract_value": 2500000,
                "start_date": "2026-01-15",
                "end_date": "2026-09-30",
            },
        )
        if r.status_code not in (200, 201):
            log("PROJECT", "Create project", "FAIL", f"{r.status_code}: {r.text[:300]}")
            return
        proj = r.json()
        entities["project"] = proj["project_id"]
        pid = entities["project"]
        log("PROJECT", "Create project", "PASS", f"code={proj['code']}")

        # Team members (needs project_id in body)
        for key, role in [
            ("pm", "project_manager"),
            ("eng_lead", "project_editor"),
            ("const_super", "project_viewer"),
        ]:
            uid = entities.get(f"uid_{key}")
            if not uid:
                continue
            r = await call(
                c,
                "POST",
                f"/projects/{pid}/members",
                "admin",
                {"user_id": uid, "project_id": pid, "role": role},
            )
            log(
                "TEAM",
                f"Add {key} as {role}",
                "PASS" if r.status_code in (200, 201) else "WARN",
                f"{r.status_code}: {r.text[:150]}",
            )

        # WBEs — Level 1
        wbe_l1 = [
            {"code": "WP-100", "name": "Ventilation System Upgrade"},
            {"code": "WP-200", "name": "Robot Arm Installation"},
            {"code": "WP-300", "name": "QA & Controls"},
        ]
        l1_ids = []
        for w in wbe_l1:
            r = await call(c, "POST", "/wbes", "admin", {**w, "project_id": pid})
            if r.status_code in (200, 201):
                wid = r.json()["wbe_id"]
                l1_ids.append(wid)
                log("WBE", f"Create L1: {w['code']}", "PASS")
            else:
                log(
                    "WBE",
                    f"Create L1: {w['code']}",
                    "FAIL",
                    f"{r.status_code}: {r.text[:200]}",
                )

        # WBEs — Level 2 under WP-200
        wbe_l2 = [
            {"code": "WP-210", "name": "Robot Procurement"},
            {"code": "WP-220", "name": "Robot Installation & Commissioning"},
            {"code": "WP-230", "name": "Safety Interlocks"},
        ]
        l2_ids = []
        for w in wbe_l2:
            r = await call(
                c,
                "POST",
                "/wbes",
                "admin",
                {**w, "project_id": pid, "parent_wbe_id": l1_ids[1]},
            )
            if r.status_code in (200, 201):
                l2_ids.append(r.json()["wbe_id"])
                log("WBE", f"Create L2: {w['code']}", "PASS")
            else:
                log(
                    "WBE",
                    f"Create L2: {w['code']}",
                    "FAIL",
                    f"{r.status_code}: {r.text[:200]}",
                )

        # Cost element types
        r = await call(c, "GET", "/cost-element-types", "admin")
        ce_types = {}
        if r.status_code == 200:
            for t in extract_data(r.json()):
                ce_types[t.get("name", "")] = t.get(
                    "cost_element_type_id", t.get("type_id", "")
                )
            log(
                "COST",
                f"Found {len(ce_types)} cost element types",
                "INFO",
                str(list(ce_types.keys())),
            )

        # Cost elements
        ce_defs = [
            {
                "wbe_id_idx": 0,
                "code": "CE-110",
                "name": "Ductwork & Fans",
                "budget": 180000,
                "type": "Equipment",
            },
            {
                "wbe_id_idx": 0,
                "code": "CE-120",
                "name": "Filtration System",
                "budget": 95000,
                "type": "Material",
            },
            {
                "wbe_id_idx": 1,
                "code": "CE-210",
                "name": "FANUC P-250iB Robots x4",
                "budget": 480000,
                "type": "Equipment",
            },
            {
                "wbe_id_idx": 2,
                "code": "CE-310",
                "name": "Vision Inspection System",
                "budget": 120000,
                "type": "Equipment",
            },
        ]
        ce_ids = []
        for ce in ce_defs:
            wbe_id = (
                l1_ids[ce["wbe_id_idx"]] if ce["wbe_id_idx"] < len(l1_ids) else None
            )
            if not wbe_id:
                continue
            type_id = (
                ce_types.get(ce["type"], next(iter(ce_types.values())))
                if ce_types
                else None
            )
            body = {
                "code": ce["code"],
                "name": ce["name"],
                "wbe_id": wbe_id,
                "project_id": pid,
                "budget_amount": str(ce["budget"]),
                "cost_element_type_id": type_id,
                "branch": "main",
            }
            r = await call(c, "POST", "/cost-elements", "admin", body)
            if r.status_code in (200, 201):
                ce_ids.append(r.json().get("cost_element_id", r.json().get("id")))
                log("COST", f"Create CE: {ce['name']} (${ce['budget']:,})", "PASS")
            else:
                log(
                    "COST",
                    f"Create CE: {ce['name']}",
                    "FAIL",
                    f"{r.status_code}: {r.text[:200]}",
                )

        # ── PHASE 2: PERMISSIONS ──
        print("\n── PHASE 2: Permission Boundaries ──")

        r = await call(
            c,
            "POST",
            "/change-orders",
            "viewer",
            {
                "title": "Viewer CO",
                "description": "Should fail",
                "project_id": pid,
                "change_type": "scope",
                "priority": "medium",
            },
        )
        log(
            "PERM",
            "Viewer cannot create CO",
            "PASS" if r.status_code == 403 else "BUG",
            f"Expected 403, got {r.status_code}",
        )

        r = await call(
            c,
            "POST",
            "/change-orders",
            "eng_lead",
            {
                "title": "Contributor CO",
                "description": "Should fail",
                "project_id": pid,
                "change_type": "scope",
                "priority": "medium",
            },
        )
        log(
            "PERM",
            "Contributor cannot create CO",
            "PASS" if r.status_code == 403 else "WARN",
            f"Expected 403, got {r.status_code} (contributor has no CO permissions)",
        )

        # ── PHASE 3: CREATE COs ──
        print("\n── PHASE 3: Create Change Orders ──")

        # CO-1: High impact (test BUG-1 fix)
        r = await call(
            c,
            "POST",
            "/change-orders",
            "admin",
            {
                "code": f"CO-{ts}-001",
                "title": "Upgrade Paint Robot Spec to P-4010",
                "description": "Client requested upgrade from FANUC P-250iB to P-4010. Affects WP-210 procurement and budget.",
                "project_id": pid,
                "change_type": "scope",
                "priority": "high",
            },
        )
        if r.status_code in (200, 201):
            entities["co1"] = r.json().get("change_order_id", r.json().get("id"))
            log(
                "CO",
                "Create CO-1 (Robot Upgrade, HIGH priority)",
                "PASS",
                f"status={r.json().get('status')}",
            )
        else:
            log("CO", "Create CO-1", "FAIL", f"{r.status_code}: {r.text[:200]}")

        # CO-2: Low impact (for reject-resubmit flow)
        r = await call(
            c,
            "POST",
            "/change-orders",
            "admin",
            {
                "code": f"CO-{ts}-002",
                "title": "Additional Safety Training",
                "description": "New regulation requires 40h training for robot operators.",
                "project_id": pid,
                "change_type": "scope",
                "priority": "low",
            },
        )
        if r.status_code in (200, 201):
            entities["co2"] = r.json().get("change_order_id", r.json().get("id"))
            log("CO", "Create CO-2 (Safety Training)", "PASS")
        else:
            log("CO", "Create CO-2", "FAIL", f"{r.status_code}: {r.text[:200]}")

        # CO-3: Draft for deletion
        r = await call(
            c,
            "POST",
            "/change-orders",
            "admin",
            {
                "code": f"CO-{ts}-003",
                "title": "Draft to Delete",
                "description": "Test deletion",
                "project_id": pid,
                "change_type": "schedule",
                "priority": "low",
            },
        )
        if r.status_code in (200, 201):
            entities["co3"] = r.json().get("change_order_id", r.json().get("id"))
            log("CO", "Create CO-3 (draft for deletion)", "PASS")
        else:
            log("CO", "Create CO-3", "FAIL", f"{r.status_code}")

        # Validation: reject CO without title
        r = await call(
            c,
            "POST",
            "/change-orders",
            "admin",
            {
                "description": "No title",
                "project_id": pid,
            },
        )
        log(
            "CO",
            "Reject CO without title",
            "PASS" if r.status_code == 422 else "BUG",
            f"Got {r.status_code}",
        )

        # ── PHASE 4: SUBMIT FOR APPROVAL ──
        print("\n── PHASE 4: Submit for Approval ──")

        # 4.1 CO-1 submit (HIGH priority — tests BUG-1 fix)
        if entities.get("co1"):
            r = await call(
                c,
                "PUT",
                f"/change-orders/{entities['co1']}/submit-for-approval",
                "admin",
            )
            if r.status_code == 200:
                d = r.json()
                log(
                    "CO-1",
                    "Submit for approval (HIGH priority — BUG-1 fix)",
                    "PASS",
                    f"status={d.get('status')}, impact={d.get('impact_level')}",
                )
            else:
                log(
                    "CO-1",
                    "Submit for approval (HIGH priority)",
                    "BUG" if r.status_code >= 500 else "FAIL",
                    f"{r.status_code}: {r.text[:300]}",
                )

        # 4.2 CO-2 submit
        if entities.get("co2"):
            r = await call(
                c,
                "PUT",
                f"/change-orders/{entities['co2']}/submit-for-approval",
                "admin",
            )
            log(
                "CO-2",
                "Submit for approval",
                "PASS" if r.status_code == 200 else "FAIL",
                f"{r.status_code}: {r.json().get('status', '') if r.status_code == 200 else r.text[:150]}",
            )

        # 4.3 Cannot resubmit
        if entities.get("co1"):
            r = await call(
                c,
                "PUT",
                f"/change-orders/{entities['co1']}/submit-for-approval",
                "admin",
            )
            log(
                "CO-1",
                "Cannot resubmit already submitted CO",
                "PASS" if r.status_code in (400, 409) else "WARN",
                f"Got {r.status_code}",
            )

        # ── PHASE 5: BUG FIXES VERIFICATION ──
        print("\n── PHASE 5: Bug Fix Verification ──")

        # BUG-4: pending-approvals
        r = await call(c, "GET", "/change-orders/pending-approvals", "admin")
        log(
            "BUG-4",
            "GET /pending-approvals (route ordering)",
            "PASS" if r.status_code == 200 else "BUG",
            f"Got {r.status_code}",
        )
        if r.status_code == 200:
            pa_data = extract_data(r.json())
            pa_count = len(pa_data) if isinstance(pa_data, list) else 0
            log("BUG-4", f"Found {pa_count} pending approvals", "INFO")

        # BUG-2: history
        if entities.get("co1"):
            r = await call(
                c, "GET", f"/change-orders/{entities['co1']}/history", "admin"
            )
            log(
                "BUG-2",
                "GET /history (hybrid property fix)",
                "PASS" if r.status_code == 200 else "BUG",
                f"Got {r.status_code}",
            )
            if r.status_code == 200:
                hist = r.json()
                log("HISTORY", f"CO-1 has {len(hist)} history entries", "INFO")

        # BUG-3: Approve from "Submitted for Approval" directly
        # NOTE: PM is the assigned approver — must use PM to approve, not admin
        if entities.get("co1"):
            r = await call(c, "PUT", f"/change-orders/{entities['co1']}/approve", "pm")
            log(
                "BUG-3",
                "PM approves from 'Submitted for Approval' directly",
                "PASS" if r.status_code == 200 else "BUG",
                f"Got {r.status_code}: {r.text[:200] if r.status_code != 200 else r.json().get('status')}",
            )

        # BUG-5: Approve/reject with no body
        if entities.get("co2"):
            # Reject with no body (BUG-5 fix test) — PM is assigned approver
            r = await call(c, "PUT", f"/change-orders/{entities['co2']}/reject", "pm")
            log(
                "BUG-5",
                "PM rejects with no body",
                "PASS" if r.status_code == 200 else "BUG",
                f"Got {r.status_code}: {r.text[:200] if r.status_code != 200 else ''}",
            )

        # ── PHASE 6: REJECT & RESUBMIT ──
        print("\n── PHASE 6: Reject & Resubmit Cycle ──")

        if entities.get("co2"):
            r = await call(c, "GET", f"/change-orders/{entities['co2']}", "admin")
            current_status = (
                r.json().get("status") if r.status_code == 200 else "unknown"
            )
            log("CO-2", f"Current status: {current_status}", "INFO")

            if current_status == "Rejected":
                r = await call(
                    c,
                    "PUT",
                    f"/change-orders/{entities['co2']}/submit-for-approval",
                    "admin",
                )
                log(
                    "CO-2",
                    "Resubmit rejected CO",
                    "PASS" if r.status_code == 200 else "FAIL",
                    f"{r.status_code}: {r.text[:150]}",
                )

                if r.status_code == 200:
                    # PM is the assigned approver after resubmit
                    r = await call(
                        c,
                        "PUT",
                        f"/change-orders/{entities['co2']}/approve",
                        "pm",
                        json_data={"comments": "Approved on second submission"},
                    )
                    log(
                        "CO-2",
                        "PM approves resubmitted CO (with body)",
                        "PASS" if r.status_code == 200 else "FAIL",
                        f"{r.status_code}: {r.text[:200] if r.status_code != 200 else ''}",
                    )

        # ── PHASE 7: IMPLEMENT & ARCHIVE ──
        print("\n── PHASE 7: Implement & Archive ──")

        for co_key in ["co1", "co2"]:
            co_id = entities.get(co_key)
            if not co_id:
                continue
            # Check status first
            r = await call(c, "GET", f"/change-orders/{co_id}", "admin")
            if r.status_code == 200 and r.json().get("status") == "Approved":
                # Admin has change-order-implement permission
                # Implement = merge isolation branch into main
                r = await call(
                    c,
                    "POST",
                    f"/change-orders/{co_id}/merge",
                    "admin",
                    json={"target_branch": "main"},
                )
                log(
                    f"{co_key.upper()}",
                    "Implement (merge)",
                    "PASS" if r.status_code == 200 else "FAIL",
                    f"{r.status_code}: {r.text[:150]}",
                )

        # Archive CO-1
        if entities.get("co1"):
            r = await call(c, "GET", f"/change-orders/{entities['co1']}", "admin")
            if r.status_code == 200 and r.json().get("status") == "Implemented":
                r = await call(
                    c, "POST", f"/change-orders/{entities['co1']}/archive", "admin"
                )
                log(
                    "CO-1",
                    "Archive implemented CO",
                    "PASS" if r.status_code == 200 else "FAIL",
                    f"{r.status_code}: {r.text[:150]}",
                )

        # ── PHASE 8: EDGE CASES ──
        print("\n── PHASE 8: Edge Cases ──")

        # Delete draft CO-3
        if entities.get("co3"):
            r = await call(c, "DELETE", f"/change-orders/{entities['co3']}", "admin")
            log(
                "CO-3",
                "Delete draft CO",
                "PASS" if r.status_code in (200, 204) else "FAIL",
                f"Got {r.status_code}",
            )

        # Cannot delete non-draft CO (NEW-BUG-2 fix)
        if entities.get("co1"):
            r = await call(c, "DELETE", f"/change-orders/{entities['co1']}", "admin")
            log(
                "NEW-BUG-2",
                "Cannot delete non-draft CO",
                "PASS" if r.status_code in (400, 404) else "BUG",
                f"Got {r.status_code}: {r.text[:150] if r.status_code not in (400, 404) else r.text[:150]}",
            )

        # Cannot approve draft
        r = await call(
            c,
            "POST",
            "/change-orders",
            "admin",
            {
                "code": f"CO-{ts}-DRAFT",
                "title": "Draft Approval Test",
                "description": "Test",
                "project_id": pid,
                "change_type": "scope",
                "priority": "low",
            },
        )
        if r.status_code in (200, 201):
            draft_id = r.json().get("change_order_id", r.json().get("id"))
            r = await call(c, "PUT", f"/change-orders/{draft_id}/approve", "admin")
            log(
                "PERM",
                "Cannot approve Draft CO",
                "PASS" if r.status_code in (400, 403) else "BUG",
                f"Got {r.status_code}",
            )

        # BUG-5: Approve with no body (separate test) — use PM as assigned approver
        r = await call(
            c,
            "POST",
            "/change-orders",
            "admin",
            {
                "code": f"CO-{ts}-B5",
                "title": "BUG-5 Test",
                "description": "Test approve with no body",
                "project_id": pid,
                "change_type": "cost",
                "priority": "low",
            },
        )
        if r.status_code in (200, 201):
            b5_id = r.json().get("change_order_id", r.json().get("id"))
            await call(c, "PUT", f"/change-orders/{b5_id}/submit-for-approval", "admin")
            # PM is the assigned approver
            r = await call(c, "PUT", f"/change-orders/{b5_id}/approve", "pm")
            log(
                "BUG-5",
                "PM approves with no body (standalone test)",
                "PASS" if r.status_code == 200 else "BUG",
                f"Got {r.status_code}: {r.text[:150] if r.status_code != 200 else ''}",
            )

        # Permission: viewer cannot submit/approve
        if entities.get("co2"):
            r = await call(
                c,
                "PUT",
                f"/change-orders/{entities['co2']}/submit-for-approval",
                "viewer",
            )
            log(
                "PERM",
                "Viewer cannot submit CO",
                "PASS" if r.status_code == 403 else "BUG",
                f"Got {r.status_code}",
            )
            r = await call(
                c, "PUT", f"/change-orders/{entities['co2']}/approve", "viewer"
            )
            log(
                "PERM",
                "Viewer cannot approve CO",
                "PASS" if r.status_code == 403 else "BUG",
                f"Got {r.status_code}",
            )

        # Viewer CAN read CO
        if entities.get("co1"):
            r = await call(c, "GET", f"/change-orders/{entities['co1']}", "viewer")
            log(
                "PERM",
                "Viewer can read CO",
                "PASS" if r.status_code == 200 else "BUG",
                f"Got {r.status_code}",
            )

        # ── PHASE 9: BRANCH ISOLATION ──
        print("\n── PHASE 9: Branch Isolation Check ──")

        if entities.get("co1"):
            r = await call(c, "GET", f"/change-orders/{entities['co1']}", "admin")
            if r.status_code == 200:
                branch = r.json().get("branch_name")
                log("BRANCH", f"CO-1 branch: {branch}", "INFO")
                if branch:
                    r_wbes = await call(
                        c,
                        "GET",
                        "/wbes",
                        "admin",
                        params={"project_id": pid, "branch": branch},
                    )
                    if r_wbes.status_code == 200:
                        bw = extract_data(r_wbes.json())
                        bc = len(bw) if isinstance(bw, list) else 0
                        log(
                            "BRANCH",
                            f"Isolation branch has {bc} WBEs",
                            "PASS" if bc > 0 else "WARN",
                        )
                    # Cost elements on isolation branch
                    r_ce = await call(
                        c,
                        "GET",
                        "/cost-elements",
                        "admin",
                        params={"project_id": pid, "branch": branch},
                    )
                    if r_ce.status_code == 200:
                        bce = extract_data(r_ce.json())
                        bcec = len(bce) if isinstance(bce, list) else 0
                        log(
                            "BRANCH",
                            f"Isolation branch has {bcec} cost elements",
                            "PASS" if bcec > 0 else "WARN",
                        )

        # ── PHASE 10: NOTIFICATIONS ──
        print("\n── PHASE 10: Notifications ──")

        r = await call(c, "GET", "/notifications", "admin", params={"limit": 10})
        if r.status_code == 200:
            nd = extract_data(r.json())
            nc = len(nd) if isinstance(nd, list) else 0
            log("NOTIF", f"Admin has {nc} notifications", "INFO")
            if isinstance(nd, list) and nc > 0:
                for n in nd[:3]:
                    log("NOTIF", f"  → {n.get('event_type')}: {n.get('title')}", "INFO")
        else:
            log(
                "NOTIF",
                "Fetch notifications",
                "WARN",
                f"{r.status_code}: {r.text[:100]}",
            )

    # ── SUMMARY ──
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\n  " + "  |  ".join(f"{k}: {v}" for k, v in sorted(counts.items())))

    for label, key in [
        ("🐛 BUGS", "BUG"),
        ("✗ FAILURES", "FAIL"),
        ("! WARNINGS", "WARN"),
    ]:
        items = [r for r in results if r["status"] == key]
        if items:
            print(f"\n  {label}:")
            for i in items:
                print(f"    - {i['test']}: {i['detail']}")

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "scenario": "Paint Booth Modernization v2",
        "summary": counts,
        "entities": {k: str(v) for k, v in entities.items()},
        "results": results,
    }
    with open("LIFECYCLE_REPORT_V2.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print("\n  Report saved to LIFECYCLE_REPORT_V2.json")
    print("=" * 70)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_simulation())
