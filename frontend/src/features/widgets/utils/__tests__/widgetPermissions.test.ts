import { describe, it, expect, vi } from "vitest";
import {
  isWidgetInScope,
  isWidgetPermitted,
} from "../widgetPermissions";
import type { WidgetScope } from "@/features/widgets/types";
import type { Permission } from "@/types/auth";

/**
 * Pure unit tests for the Phase 5 permission + scope helpers.
 *
 * Scope and permission are **independent** gates per the locked design:
 * `isWidgetInScope` knows nothing about the user, and `isWidgetPermitted`
 * knows nothing about the dashboard scope.
 */

function scopeDef(scope: WidgetScope | undefined) {
  return { scope } as { scope: WidgetScope };
}

function permDef(requiredPermission: Permission | Permission[] | undefined) {
  return { requiredPermission } as {
    requiredPermission: Permission | Permission[];
  };
}

const grant = (held: string[]) => ({
  hasPermission: (p: Permission | string) => held.includes(p),
  hasAllPermissions: (ps: (Permission | string)[]) =>
    ps.every((p) => held.includes(p)),
});

describe("isWidgetInScope", () => {
  it("unset scope defaults to project: shown on project, hidden on portfolio", () => {
    expect(isWidgetInScope(scopeDef(undefined), "project")).toBe(true);
    expect(isWidgetInScope(scopeDef(undefined), "portfolio")).toBe(false);
  });

  it('"project" widget: shown on project, hidden on portfolio', () => {
    expect(isWidgetInScope(scopeDef("project"), "project")).toBe(true);
    expect(isWidgetInScope(scopeDef("project"), "portfolio")).toBe(false);
  });

  it('"portfolio" widget: shown on portfolio, hidden on project', () => {
    expect(isWidgetInScope(scopeDef("portfolio"), "portfolio")).toBe(true);
    expect(isWidgetInScope(scopeDef("portfolio"), "project")).toBe(false);
  });

  it('"any" widget: shown on both scopes', () => {
    expect(isWidgetInScope(scopeDef("any"), "project")).toBe(true);
    expect(isWidgetInScope(scopeDef("any"), "portfolio")).toBe(true);
  });
});

describe("isWidgetPermitted", () => {
  it("no requiredPermission → permitted", () => {
    // The check fns are not even consulted when there is no requirement.
    expect(
      isWidgetPermitted(permDef(undefined), vi.fn(), vi.fn()),
    ).toBe(true);
  });

  it("single permission held → permitted", () => {
    const { hasPermission, hasAllPermissions } = grant(["portfolio-read"]);
    expect(
      isWidgetPermitted(
        permDef("portfolio-read"),
        hasPermission,
        hasAllPermissions,
      ),
    ).toBe(true);
  });

  it("single permission missing → denied", () => {
    const { hasPermission, hasAllPermissions } = grant([]);
    expect(
      isWidgetPermitted(
        permDef("portfolio-read"),
        hasPermission,
        hasAllPermissions,
      ),
    ).toBe(false);
  });

  it("array: all held → permitted", () => {
    const { hasPermission, hasAllPermissions } = grant([
      "project-read",
      "cost-registration-read",
    ]);
    expect(
      isWidgetPermitted(
        permDef(["project-read", "cost-registration-read"]),
        hasPermission,
        hasAllPermissions,
      ),
    ).toBe(true);
  });

  it("array: one missing → denied", () => {
    const { hasPermission, hasAllPermissions } = grant(["project-read"]);
    expect(
      isWidgetPermitted(
        permDef(["project-read", "cost-registration-read"]),
        hasPermission,
        hasAllPermissions,
      ),
    ).toBe(false);
  });
});
