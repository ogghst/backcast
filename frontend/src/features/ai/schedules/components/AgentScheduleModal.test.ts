import { describe, it, expect } from "vitest";
import { buildScheduleContext } from "./buildScheduleContext";
import type { AgentScheduleFormValues } from "./AgentScheduleFormValues";

const baseValues = {
  name: "n",
  prompt: "p",
  assistant_config_id: "a1",
  execution_mode: "standard",
  cron_expr: "0 9 * * *",
  timezone: "UTC",
  is_active: true,
} as const;

function makeValues(
  scope: AgentScheduleFormValues["context_scope"],
  extra: Partial<AgentScheduleFormValues> = {},
): AgentScheduleFormValues {
  return { ...baseValues, context_scope: scope, ...extra };
}

describe("buildScheduleContext", () => {
  it("builds a general/global context with null project_id", () => {
    const { project_id, context } = buildScheduleContext(makeValues("global"));
    expect(project_id).toBeNull();
    expect(context).toEqual({ type: "general" });
  });

  it("builds a project context using scope_project_id + name", () => {
    const { project_id, context } = buildScheduleContext(
      makeValues("project", {
        scope_project_id: "pid-1",
        scope_project_name: "Project One",
      }),
    );
    expect(project_id).toBe("pid-1");
    expect(context).toEqual({ type: "project", id: "pid-1", name: "Project One" });
  });

  it("builds a wbe context carrying both wbe id and project_id", () => {
    const { project_id, context } = buildScheduleContext(
      makeValues("wbe", {
        scope_project_id: "pid-1",
        scope_project_name: "Project One",
        scope_wbe_id: "wbe-9",
        scope_wbe_name: "Engineering",
      }),
    );
    expect(project_id).toBe("pid-1");
    expect(context).toEqual({
      type: "wbe",
      id: "wbe-9",
      project_id: "pid-1",
      name: "Engineering",
    });
  });

  it("falls back to global for an unrecognized scope", () => {
    // Cast through unknown to feed an out-of-union scope value to verify the
    // default branch is safe.
    const values = {
      ...makeValues("global"),
      context_scope: "bogus",
    } as unknown as AgentScheduleFormValues;
    const { project_id, context } = buildScheduleContext(values);
    expect(project_id).toBeNull();
    expect(context).toEqual({ type: "general" });
  });
});
