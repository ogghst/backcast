#!/usr/bin/env python3
"""
Full Change Order Lifecycle Simulation v2
==========================================
Realistic project scenario: Industrial Robot Assembly Line
Tests full CO lifecycle, permissions, edge cases, and state transitions.
"""

import json
import sys
import traceback
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "http://localhost:8020/api/v1"

# ─── Helpers ────────────────────────────────────────────────────────────


def api(method, path, token=None, data=None, params=None):
    url = BASE + path
    if params:
        url += "?" + urlencode(params)
    # Always send body for PUT/POST with JSON content type if data is provided (even empty dict)
    if data is not None:
        body = json.dumps(data).encode()
        headers = {"Content-Type": "application/json"}
    else:
        body = None
        headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=body, headers=headers, method=method)
    try:
        resp = urlopen(req)
        raw = resp.read().decode()
        try:
            return resp.status, json.loads(raw)
        except (ValueError, KeyError):
            return resp.status, raw
    except HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except (ValueError, KeyError):
            return e.code, raw


def login(email, password):
    body = urlencode({"username": email, "password": password}).encode()
    req = Request(
        BASE + "/auth/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp = urlopen(req)
    return json.loads(resp.read())["access_token"]


def section(title):
    print(f"\n{'#' * 60}\n# {title}\n{'#' * 60}")


issues = []
changes = []


def report_issue(severity, area, desc, detail=""):
    issues.append(
        {
            "severity": severity,
            "area": area,
            "description": desc,
            "detail": str(detail)[:300],
        }
    )
    icon = {"BUG": "BUG", "WARN": "WARN"}.get(severity, "INFO")
    print(f"  [{icon}] {area}: {desc}")
    if detail:
        print(f"         {str(detail)[:200]}")


def report_change(action, entity, detail):
    changes.append({"action": action, "entity": entity, "detail": detail})
    print(f"  [+] {action} {entity}: {detail}")


def main():
    section("PHASE 0: Authentication")
    admin_tk = login("admin@backcast.org", "adminadmin")
    pm_tk = login("pm@backcast.org", "backcast")
    viewer_tk = login("viewer@backcast.org", "backcast")
    eng_tk = login("eng.lead@backcast.org", "backcast")
    const_tk = login("const.super@backcast.org", "backcast")

    status, me = api("GET", "/auth/me", admin_tk)
    print(f"  Admin: {me.get('email')} role={me.get('role')}")
    status, me = api("GET", "/auth/me", pm_tk)
    print(f"  PM:    {me.get('email')} role={me.get('role')}")
    status, me = api("GET", "/auth/me", viewer_tk)
    print(f"  Viewer:{me.get('email')} role={me.get('role')}")

    # ─── PHASE 1: Project & Team ──────────────────────────────────────

    section("PHASE 1: Create Project & Assign Team")

    # Use unique code with timestamp to avoid collisions
    import time

    run_id = str(int(time.time()))[-6:]
    proj_code = f"PRJ-ROBOT-B-{run_id}"

    status, project = api(
        "POST",
        "/projects",
        admin_tk,
        {
            "name": f"Industrial Robot Assembly Line - Line B (test {run_id})",
            "code": proj_code,
            "description": "Full assembly line automation for Line B",
            "contract_value": "850000.00",
            "budget": "120000.00",
            "start_date": "2026-03-01T00:00:00Z",
            "end_date": "2027-06-30T00:00:00Z",
        },
    )
    if status not in (200, 201):
        print(f"  FATAL: Cannot create project: {status} {project}")
        sys.exit(1)
    pid = project["project_id"]
    report_change("CREATE", "Project", f"'{project['name']}' ({pid[:8]}...)")

    # Add team members (requires project_id in body AND path)
    for uid, role, email in [
        ("533a7e61-6b73-5978-a751-7862efa734f7", "project_manager", "pm@backcast.org"),
        (
            "dce2e861-bdb7-5887-beaf-6a22837d266d",
            "project_editor",
            "eng.lead@backcast.org",
        ),
        (
            "10bce202-8321-5208-8c9c-1fa8269e48fa",
            "project_viewer",
            "const.super@backcast.org",
        ),
    ]:
        status, res = api(
            "POST",
            f"/projects/{pid}/members",
            admin_tk,
            {
                "user_id": uid,
                "role": role,
                "project_id": pid,
            },
        )
        if status in (200, 201):
            report_change("ADD", "Team", f"{email} as {role}")
        else:
            report_issue(
                "BUG", "Team Assignment", f"Failed to add {email}: {status}", str(res)
            )

    status, members = api("GET", f"/projects/{pid}/members", admin_tk)
    print(f"  Team: {len(members)} members")

    # ─── PHASE 2: WBE Hierarchy ──────────────────────────────────────

    section("PHASE 2: WBE Hierarchy")

    l1_wbes = [
        ("Site Preparation & Civil Works", f"{proj_code}-1.0"),
        ("Robot Cell Installation", f"{proj_code}-2.0"),
        ("Conveyor System", f"{proj_code}-3.0"),
        ("HMI & Control Systems", f"{proj_code}-4.0"),
    ]
    l1_ids = []
    for name, code in l1_wbes:
        status, res = api(
            "POST", "/wbes", admin_tk, {"name": name, "code": code, "project_id": pid}
        )
        if status in (200, 201):
            wid = res.get("wbe_id", res.get("id"))
            l1_ids.append(wid)
            report_change("CREATE", "WBE", f"{code} {name}")
        else:
            report_issue("BUG", "WBE", f"Failed {code}: {status}", str(res))

    # L2 under Robot Cell (l1_ids[1])
    robot_id = l1_ids[1]
    l2_robot = [
        ("Robot Base & Foundation", f"{proj_code}-2.1"),
        ("Robot Arm Assembly", f"{proj_code}-2.2"),
        ("End Effector & Tooling", f"{proj_code}-2.3"),
    ]
    l2_ids = []
    for name, code in l2_robot:
        status, res = api(
            "POST",
            "/wbes",
            admin_tk,
            {"name": name, "code": code, "project_id": pid, "parent_id": robot_id},
        )
        if status in (200, 201):
            l2_ids.append(res.get("wbe_id", res.get("id")))
            report_change("CREATE", "WBE", f"{code} {name}")

    # L2 under Conveyor (l1_ids[2])
    conv_id = l1_ids[2]
    l2_conv = [
        ("Main Conveyor Belt", f"{proj_code}-3.1"),
        ("Transfer Stations", f"{proj_code}-3.2"),
    ]
    l2_conv_ids = []
    for name, code in l2_conv:
        status, res = api(
            "POST",
            "/wbes",
            admin_tk,
            {"name": name, "code": code, "project_id": pid, "parent_id": conv_id},
        )
        if status in (200, 201):
            l2_conv_ids.append(res.get("wbe_id", res.get("id")))
            report_change("CREATE", "WBE", f"{code} {name}")

    # ─── PHASE 3: Cost Elements ──────────────────────────────────────

    section("PHASE 3: Cost Elements & Budget")

    # Get cost element types
    status, cetypes = api("GET", "/cost-element-types", admin_tk)
    cet_map = {}
    if isinstance(cetypes, dict) and "items" in cetypes:
        for ct in cetypes["items"]:
            cet_map[ct["name"]] = ct.get("cost_element_type_id", ct.get("id"))
    elif isinstance(cetypes, list):
        for ct in cetypes:
            cet_map[ct["name"]] = ct.get("cost_element_type_id", ct.get("id"))
    print(f"  Cost element types: {list(cet_map.keys())}")

    def get_cet_id(name_fallback, idx=0):
        if name_fallback in cet_map:
            return cet_map[name_fallback]
        return list(cet_map.values())[idx] if cet_map else None

    ce_ids = []
    cost_items = [
        (l2_ids[0], "CE-B-2.1.1", "Concrete Foundation Work", "Material", 15000.00),
        (
            l2_ids[1],
            "CE-B-2.2.1",
            "Robot Arm Procurement (M-20iA)",
            "Equipment",
            45000.00,
        ),
        (
            l2_ids[2] if len(l2_ids) > 2 else l2_ids[0],
            "CE-B-2.3.1",
            "Gripper & Tooling Kit",
            "Equipment",
            12000.00,
        ),
    ]
    if l2_conv_ids:
        cost_items.append(
            (
                l2_conv_ids[0],
                "CE-B-3.1.1",
                "Belt Material & Install",
                "Material",
                28000.00,
            )
        )

    for wbe_id, code, name, cet_name, amount in cost_items:
        cet_id = get_cet_id(cet_name)
        if not cet_id:
            report_issue("WARN", "Cost Element", f"No CET found for '{cet_name}'")
            continue
        payload = {
            "wbe_id": wbe_id,
            "code": code,
            "name": name,
            "budget_amount": amount,
            "cost_element_type_id": cet_id,
            "branch": "main",
        }
        status, res = api("POST", "/cost-elements", admin_tk, payload)
        if status in (200, 201):
            ce_ids.append(res.get("cost_element_id", res.get("id")))
            report_change("CREATE", "Cost Element", f"{code} {name} ${amount:,.0f}")
        else:
            report_issue("BUG", "Cost Element", f"Failed '{name}': {status}", str(res))

    # ─── PHASE 4: Create Change Orders ───────────────────────────────

    section("PHASE 4: Change Order Creation (PM)")

    # CO1: HIGH - Robot arm upgrade
    co1_data = {
        "code": f"CO-B-{run_id}-001",
        "project_id": pid,
        "title": "Robot Arm Upgrade - Higher Payload Capacity",
        "description": "Upgrading from M-20iA to M-40iA requires additional foundation reinforcement.",
        "justification": "Product weight changed from 15kg to 35kg. Assembly quality compromised without upgrade.",
        "impact_level": "HIGH",
        "effective_date": "2026-07-01T00:00:00Z",
    }
    status, co1 = api("POST", "/change-orders", pm_tk, co1_data)
    if status in (200, 201):
        co1_id = co1.get("change_order_id", co1.get("id"))
        report_change("CREATE", "CO", f"CO-B-001 '{co1_data['title']}' (HIGH)")
        print(
            f"  Status: {co1.get('status')}, Branch: {co1.get('branch', co1.get('branch_name'))}"
        )
    else:
        report_issue("BUG", "CO Create", f"PM failed to create CO: {status}", str(co1))
        co1_id = None

    # CO2: LOW - Minor alignment
    co2_data = {
        "code": f"CO-B-{run_id}-002",
        "project_id": pid,
        "title": "Conveyor Alignment Adjustment - Bay 3",
        "description": "15cm lateral shift to match updated floor layout.",
        "justification": "Facilities team updated floor markings.",
        "impact_level": "LOW",
    }
    status, co2 = api("POST", "/change-orders", pm_tk, co2_data)
    if status in (200, 201):
        co2_id = co2.get("change_order_id", co2.get("id"))
        report_change("CREATE", "CO", f"CO-B-002 '{co2_data['title']}' (LOW)")
    else:
        report_issue("BUG", "CO Create", f"Failed CO2: {status}", str(co2))
        co2_id = None

    # CO3: CRITICAL - Safety relay
    co3_data = {
        "code": f"CO-B-{run_id}-003",
        "project_id": pid,
        "title": "Emergency Safety Relay Addition",
        "description": "Safety audit identified missing relay on cell boundary.",
        "justification": "Regulatory compliance from audit SA-2026-015.",
        "impact_level": "CRITICAL",
    }
    status, co3 = api("POST", "/change-orders", pm_tk, co3_data)
    if status in (200, 201):
        co3_id = co3.get("change_order_id", co3.get("id"))
        report_change("CREATE", "CO", f"CO-B-003 '{co3_data['title']}' (CRITICAL)")
    else:
        report_issue("BUG", "CO Create", f"Failed CO3: {status}", str(co3))
        co3_id = None

    # ─── PHASE 5: Permission Tests ───────────────────────────────────

    section("PHASE 5: Permission & RBAC Tests")

    # 5a: Viewer cannot create CO
    status, res = api(
        "POST",
        "/change-orders",
        viewer_tk,
        {
            "code": "CO-ILLEGAL",
            "project_id": pid,
            "title": "Nope",
            "description": "x",
        },
    )
    if status in (200, 201):
        report_issue("BUG", "RBAC", "Viewer created a CO (should be 403)")
    else:
        print(f"  PASS: Viewer cannot create CO ({status})")

    # 5b: Viewer cannot submit CO
    if co1_id:
        status, res = api(
            "PUT", f"/change-orders/{co1_id}/submit-for-approval", viewer_tk
        )
        if status in (200, 201):
            report_issue("BUG", "RBAC", "Viewer submitted a CO (should be 403)")
        else:
            print(f"  PASS: Viewer cannot submit CO ({status})")

    # 5c: Viewer cannot approve CO
    if co1_id:
        status, res = api("PUT", f"/change-orders/{co1_id}/approve", viewer_tk, {})
        if status in (200, 201):
            report_issue("BUG", "RBAC", "Viewer approved a CO (should be 403)")
        else:
            print(f"  PASS: Viewer cannot approve CO ({status})")

    # 5d: Engineering Lead (project_editor) can create CO
    status, res = api(
        "POST",
        "/change-orders",
        eng_tk,
        {
            "code": f"CO-B-{run_id}-004",
            "project_id": pid,
            "title": "Wiring Harness Update",
            "description": "Updated wiring diagram from engineering.",
            "impact_level": "LOW",
        },
    )
    if status in (200, 201):
        co4_id = res.get("change_order_id", res.get("id"))
        report_change("CREATE", "CO", "CO-B-004 by Eng Lead (project_editor)")
        print("  PASS: Eng Lead (project_editor) can create CO")
    else:
        report_issue(
            "WARN", "RBAC", f"Eng Lead could not create CO: {status}", str(res)
        )
        co4_id = None

    # 5e: Construction Super (project_viewer) cannot create CO
    status, res = api(
        "POST",
        "/change-orders",
        const_tk,
        {
            "code": f"CO-B-{run_id}-005",
            "project_id": pid,
            "title": "Unauthorized",
            "description": "x",
        },
    )
    if status in (200, 201):
        report_issue(
            "BUG", "RBAC", "project_viewer (Const Super) created a CO (should be 403)"
        )
    else:
        print(f"  PASS: project_viewer cannot create CO ({status})")

    # ─── PHASE 6: Full CO1 Lifecycle ─────────────────────────────────

    section("PHASE 6: CO1 Full Lifecycle (HIGH impact)")

    if co1_id:
        # Submit for approval
        status, res = api("PUT", f"/change-orders/{co1_id}/submit-for-approval", pm_tk)
        if status in (200, 201):
            report_change("TRANSITION", "CO1", "Draft → Submitted for Approval")
            print(
                f"  CO1 submitted. New status: {res.get('status') if isinstance(res, dict) else 'OK'}"
            )
        else:
            report_issue("BUG", "CO Submit", f"Failed: {status}", str(res))

        # Check impact analysis
        # Check impact analysis (needs branch_name param)
        co1_branch = co1.get("branch", co1.get("branch_name", "main"))
        status, impact = api(
            "GET",
            f"/change-orders/{co1_id}/impact",
            admin_tk,
            params={"branch_name": co1_branch},
        )
        if status == 200 and isinstance(impact, dict):
            print(
                f"  Impact: score={impact.get('impact_score')}, level={impact.get('impact_level')}"
            )
        else:
            report_issue("WARN", "Impact", f"API returned {status}", str(impact)[:200])

        # Check approval info
        status, approval = api(
            "GET", f"/change-orders/{co1_id}/approval-info", admin_tk
        )
        if status == 200 and isinstance(approval, dict):
            approvers = approval.get("eligible_approvers", [])
            print(f"  Eligible approvers: {len(approvers)}")
            for a in approvers[:3]:
                print(f"    - {a.get('email', a.get('name', str(a)[:40]))}")
        else:
            report_issue(
                "WARN", "Approval Info", f"API returned {status}", str(approval)[:200]
            )

        # PM tries to approve own CO
        status, res = api("PUT", f"/change-orders/{co1_id}/approve", pm_tk, {})
        if status in (200, 201):
            report_issue(
                "BUG", "RBAC", "PM approved their own CO (conflict of interest)"
            )
        else:
            print(f"  PASS: PM cannot approve own CO ({status})")

        # Admin approves (body required by schema even if fields are optional)
        status, res = api("PUT", f"/change-orders/{co1_id}/approve", admin_tk, {})
        if status in (200, 201):
            report_change("TRANSITION", "CO1", "Submitted → Approved (by admin)")
            print("  CO1 approved!")
        else:
            report_issue(
                "BUG", "CO Approve", f"Admin approve failed: {status}", str(res)
            )

        # Verify status
        status, co1_state = api("GET", f"/change-orders/{co1_id}", admin_tk)
        print(
            f"  CO1 status: {co1_state.get('status')}, branch: {co1_state.get('branch', co1_state.get('branch_name'))}"
        )

        # Cannot re-submit approved CO
        status, res = api(
            "PUT", f"/change-orders/{co1_id}/submit-for-approval", admin_tk
        )
        if status in (200, 201):
            report_issue("BUG", "State", "Re-submitted an already APPROVED CO")
        else:
            print(f"  PASS: Cannot re-submit approved CO ({status})")

    # ─── PHASE 7: CO2 Rejection ──────────────────────────────────────

    section("PHASE 7: CO2 Rejection Flow (LOW impact)")

    if co2_id:
        status, res = api("PUT", f"/change-orders/{co2_id}/submit-for-approval", pm_tk)
        if status in (200, 201):
            report_change("TRANSITION", "CO2", "Draft → Submitted")

        # Cannot approve rejected CO (body required)
        status, res = api("PUT", f"/change-orders/{co2_id}/approve", admin_tk, {})

        # Reject as admin
        status, res = api(
            "PUT",
            f"/change-orders/{co2_id}/reject",
            admin_tk,
            {
                "comments": "Already covered in original scope tolerances.",
            },
        )
        if status in (200, 201):
            report_change("TRANSITION", "CO2", "Submitted → Rejected")
            print("  CO2 rejected!")
        else:
            report_issue("BUG", "CO Reject", f"Failed: {status}", str(res))

        # Verify rejected status
        status, co2_state = api("GET", f"/change-orders/{co2_id}", admin_tk)
        print(f"  CO2 status: {co2_state.get('status')}")

        # Cannot approve rejected CO (body required)
        status, res = api("PUT", f"/change-orders/{co2_id}/approve", admin_tk, {})
        if status in (200, 201):
            report_issue("BUG", "State", "Approved a REJECTED CO")
        else:
            print(f"  PASS: Cannot approve rejected CO ({status})")

        # Can re-submit rejected CO (intentional: allows rework & resubmit)
        status, res = api("PUT", f"/change-orders/{co2_id}/submit-for-approval", pm_tk)
        if status in (200, 201):
            report_change(
                "TRANSITION", "CO2", "Rejected → Re-submitted (rework allowed)"
            )
            print("  INFO: Rejected CO can be re-submitted (rework flow)")
        else:
            print(f"  Re-submit rejected CO: {status}")

    # ─── PHASE 8: CO3 CRITICAL - Full lifecycle ──────────────────────

    section("PHASE 8: CO3 CRITICAL Lifecycle & Escalation")

    if co3_id:
        status, res = api("PUT", f"/change-orders/{co3_id}/submit-for-approval", pm_tk)
        if status in (200, 201):
            report_change("TRANSITION", "CO3", "Draft → Submitted (CRITICAL)")
            print("  CO3 submitted (CRITICAL)")

        # Impact analysis on CRITICAL (needs branch_name)
        co3_branch = co3.get("branch", co3.get("branch_name", "main"))
        status, impact = api(
            "GET",
            f"/change-orders/{co3_id}/impact",
            admin_tk,
            params={"branch_name": co3_branch},
        )
        if status == 200 and isinstance(impact, dict):
            print(
                f"  Impact: score={impact.get('impact_score')}, level={impact.get('impact_level')}"
            )

        # Try escalate
        status, res = api("POST", f"/change-orders/{co3_id}/escalate", pm_tk)
        if status in (200, 201):
            report_change("ESCALATE", "CO3", "Escalated by PM")
            print("  CO3 escalated by PM")
        else:
            print(f"  Escalate (PM): {status}")

        # Approve as admin (body required)
        status, res = api("PUT", f"/change-orders/{co3_id}/approve", admin_tk, {})
        if status in (200, 201):
            report_change("TRANSITION", "CO3", "Submitted → Approved (CRITICAL)")
            print("  CO3 approved!")
        else:
            report_issue("BUG", "CO Approve", f"CO3 approve failed: {status}", str(res))

    # ─── PHASE 9: CO4 by Eng Lead - different submitter ──────────────

    section("PHASE 9: CO4 Lifecycle (created by Eng Lead)")

    if co4_id:
        # Eng Lead submits their own CO
        status, res = api("PUT", f"/change-orders/{co4_id}/submit-for-approval", eng_tk)
        if status in (200, 201):
            report_change("TRANSITION", "CO4", "Draft → Submitted (by Eng Lead)")
            print("  CO4 submitted by Eng Lead")

            # PM approves (different user, has manager role)
            status, res = api("PUT", f"/change-orders/{co4_id}/approve", pm_tk, {})
            if status in (200, 201):
                report_change("TRANSITION", "CO4", "Submitted → Approved (by PM)")
                print("  CO4 approved by PM (not creator)")
            else:
                # PM might not have change-order-approve permission
                print(f"  PM approve: {status} - {str(res)[:200]}")
                # Admin approves instead
                status, res = api(
                    "PUT", f"/change-orders/{co4_id}/approve", admin_tk, {}
                )
                if status in (200, 201):
                    report_change(
                        "TRANSITION", "CO4", "Submitted → Approved (by admin)"
                    )
                    print("  CO4 approved by admin")
                else:
                    report_issue(
                        "BUG", "CO Approve", f"CO4 approve failed: {status}", str(res)
                    )
        else:
            report_issue(
                "BUG", "CO Submit", f"Eng Lead submit failed: {status}", str(res)
            )

    # ─── PHASE 10: Audit Trail ───────────────────────────────────────

    section("PHASE 10: Audit Trail")

    for co_label, co_id in [("CO1", co1_id), ("CO2", co2_id), ("CO3", co3_id)]:
        if not co_id:
            continue
        status, history = api("GET", f"/change-orders/{co_id}/history", admin_tk)
        if status == 200:
            items = history if isinstance(history, list) else history.get("items", [])
            print(f"  {co_label} history: {len(items)} entries")
            for h in items[:5]:
                action = h.get("action", h.get("status", h.get("old_status", "?")))
                by = h.get(
                    "performed_by", h.get("changed_by", h.get("created_by", "?"))
                )
                print(f"    → {action} by {str(by)[:8]}...")
        else:
            report_issue(
                "WARN",
                "Audit",
                f"{co_label} history returned {status}",
                str(history)[:200],
            )

    # ─── PHASE 11: Edge Cases ────────────────────────────────────────

    section("PHASE 11: Edge Cases & Validation")

    # 11a: CO without project
    status, res = api(
        "POST",
        "/change-orders",
        pm_tk,
        {"code": f"CO-X-{run_id}", "title": "No project"},
    )
    if status in (200, 201):
        report_issue("BUG", "Validation", "CO created without project_id")
    else:
        print(f"  PASS: CO without project_id rejected ({status})")

    # 11b: Empty title
    status, res = api(
        "POST",
        "/change-orders",
        pm_tk,
        {"code": f"CO-Y-{run_id}", "project_id": pid, "title": ""},
    )
    if status in (200, 201):
        report_issue("BUG", "Validation", "CO created with empty title")
    else:
        print(f"  PASS: Empty title rejected ({status})")

    # 11c: Duplicate code
    status, res = api(
        "POST",
        "/change-orders",
        pm_tk,
        {
            "code": f"CO-B-{run_id}-001",
            "project_id": pid,
            "title": "Duplicate code test",
        },
    )
    if status in (200, 201):
        report_issue("BUG", "Validation", "CO created with duplicate code 'CO-B-001'")
    else:
        print(f"  PASS: Duplicate code rejected ({status})")

    # 11d: Delete draft CO
    status, draft = api(
        "POST",
        "/change-orders",
        pm_tk,
        {
            "code": f"CO-B-{run_id}-DEL",
            "project_id": pid,
            "title": "To be deleted",
        },
    )
    if status in (200, 201):
        draft_id = draft.get("change_order_id", draft.get("id"))
        status, res = api("DELETE", f"/change-orders/{draft_id}", admin_tk)
        if status in (200, 204):
            report_change("DELETE", "CO", "Draft CO deleted")
            print("  PASS: Draft CO deleted")
        else:
            report_issue("BUG", "CO Delete", f"Cannot delete draft: {status}", str(res))

    # 11e: Cannot delete non-draft CO
    if co2_id:
        status, co2s = api("GET", f"/change-orders/{co2_id}", admin_tk)
        if co2s.get("status") not in ("Draft",):
            status, res = api("DELETE", f"/change-orders/{co2_id}", pm_tk)
            if status in (200, 204):
                report_issue(
                    "BUG",
                    "State",
                    f"Deleted a {co2s.get('status')} CO (should only delete Draft)",
                )
            else:
                print(f"  PASS: Cannot delete {co2s.get('status')} CO ({status})")

    # 11f: CO on different project where user is not member
    status, res = api(
        "POST",
        "/change-orders",
        pm_tk,
        {
            "code": f"CO-CROSS-{run_id}",
            "project_id": "b5e967fe-526c-4f59-9ad4-9f5288e41332",
            "title": "Cross-project CO",
        },
    )
    if status in (200, 201):
        # PM might have access to all projects? Check
        print(
            "  INFO: PM can create CO on project where they're not explicitly a member"
        )
    else:
        print(f"  PM cross-project CO: {status}")

    # 11g: Negative test - approve without submitting first
    status, fresh_co = api(
        "POST",
        "/change-orders",
        pm_tk,
        {
            "code": f"CO-B-{run_id}-FRESH",
            "project_id": pid,
            "title": "Fresh draft",
        },
    )
    if status in (200, 201):
        fresh_id = fresh_co.get("change_order_id", fresh_co.get("id"))
        status, res = api("PUT", f"/change-orders/{fresh_id}/approve", admin_tk, {})
        if status in (200, 201):
            report_issue(
                "BUG",
                "State",
                "Approved a CO that was never submitted (still in Draft)",
            )
        else:
            print(f"  PASS: Cannot approve Draft CO ({status})")

    # ─── PHASE 12: Stats & Notifications ─────────────────────────────

    section("PHASE 12: Stats & Notifications")

    status, stats = api(
        "GET", "/change-orders/stats", admin_tk, params={"project_id": pid}
    )
    if status == 200 and isinstance(stats, dict):
        print(
            f"  CO Stats: total={stats.get('total_count')}, by_status={stats.get('by_status')}"
        )
    else:
        report_issue("WARN", "Stats", f"Stats returned {status}", str(stats)[:200])

    status, pending = api("GET", "/change-orders/pending-approvals", admin_tk)
    if status == 200:
        items = (
            pending
            if isinstance(pending, list)
            else pending.get("items", [])
            if isinstance(pending, dict)
            else []
        )
        print(f"  Pending approvals: {len(items)}")
    else:
        report_issue("WARN", "Pending", f"API returned {status}", str(pending)[:200])

    # Notifications
    for label, tk in [("Admin", admin_tk), ("PM", pm_tk), ("Eng Lead", eng_tk)]:
        status, notifs = api("GET", "/notifications", tk)
        if status == 200:
            if isinstance(notifs, list):
                print(f"  {label} notifications: {len(notifs)}")
            elif isinstance(notifs, dict):
                items = notifs.get("items", notifs.get("notifications", []))
                print(f"  {label} notifications: {len(items)}")
        else:
            print(f"  {label} notifications: status={status}")

    # ─── PHASE 13: CO Archive ────────────────────────────────────────

    section("PHASE 13: Archive & Recover")

    if co2_id:
        status, res = api("POST", f"/change-orders/{co2_id}/archive", admin_tk)
        if status in (200, 201):
            report_change("ARCHIVE", "CO2", "Rejected CO archived")
            print("  CO2 archived!")
        else:
            print(f"  Archive: {status}")

    if co1_id:
        status, res = api("POST", f"/change-orders/{co1_id}/recover", admin_tk)
        if status in (200, 201):
            report_change("RECOVER", "CO1", "Recover executed")
            print("  CO1 recover: OK")
        else:
            print(f"  Recover: {status}")

    # ─── PHASE 14: Final Verification ────────────────────────────────

    section("PHASE 14: Final State Verification")

    status, all_cos = api("GET", "/change-orders", admin_tk, params={"project_id": pid})
    if status == 200:
        items = all_cos if isinstance(all_cos, list) else all_cos.get("items", [])
        print(f"\n  Final COs ({len(items)}):")
        for co in items:
            print(
                f"    {co.get('code', '?'):12s} | {co.get('status', '?'):30s} | {co.get('title', '?')[:45]} | impact={co.get('impact_level', '?')}"
            )

    # Check WBEs intact
    status, wbes = api("GET", "/wbes", admin_tk, params={"project_id": pid})
    if status == 200:
        items = wbes if isinstance(wbes, list) else wbes.get("items", [])
        print(f"\n  WBEs: {len(items)} total")

    # Check cost elements intact
    if ce_ids:
        for ce_id in ce_ids[:2]:
            status, ce = api("GET", f"/cost-elements/{ce_id}", admin_tk)
            if status == 200:
                print(
                    f"  Cost element: {ce.get('name')} budget={ce.get('budget_amount', ce.get('amount', '?'))}"
                )

    # ─── REPORT ──────────────────────────────────────────────────────

    section("SIMULATION COMPLETE")

    bugs = [i for i in issues if i["severity"] == "BUG"]
    warns = [i for i in issues if i["severity"] == "WARN"]

    print(f"\n  Changes made: {len(changes)}")
    print(f"  Issues found: {len(issues)} ({len(bugs)} BUGs, {len(warns)} Warnings)")
    print()

    if bugs:
        print("  === BUGS ===")
        for b in bugs:
            print(f"    [{b['area']}] {b['description']}")
            if b.get("detail"):
                print(f"      Detail: {b['detail'][:150]}")

    if warns:
        print("\n  === WARNINGS ===")
        for w in warns:
            print(f"    [{w['area']}] {w['description']}")

    return issues, changes


if __name__ == "__main__":
    try:
        issues, changes = main()
    except Exception as e:
        print(f"\nFATAL: {e}")
        traceback.print_exc()
