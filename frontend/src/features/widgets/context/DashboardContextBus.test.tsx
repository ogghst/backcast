import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { DashboardContextBus } from "./DashboardContextBus";
import { useDashboardContext } from "./useDashboardContext";

/**
 * Mock TimeMachineContext since DashboardContextBus consumes it internally.
 */
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: vi.fn(),
  }),
}));

/** Helper to render with Ant Design ConfigProvider */
function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

/** Test component that reads and displays context values */
function ContextReader() {
  const ctx = useDashboardContext();
  return (
    <div>
      <span data-testid="project-id">{ctx.projectId}</span>
      <span data-testid="wbe-id">{ctx.wbeId ?? "undefined"}</span>
      <span data-testid="cost-element-id">
        {ctx.costElementId ?? "undefined"}
      </span>
      <span data-testid="branch">{ctx.branch}</span>
      <span data-testid="mode">{ctx.mode}</span>
      <span data-testid="as-of">{ctx.asOf ?? "undefined"}</span>
    </div>
  );
}

/** Test component that calls setWbeId */
function WbeIdSetter() {
  const ctx = useDashboardContext();
  return (
    <div>
      <span data-testid="wbe-id">{ctx.wbeId ?? "undefined"}</span>
      <button
        data-testid="set-wbe"
        onClick={() => ctx.setWbeId("wbe-123")}
      />
    </div>
  );
}

/** Test component that calls setCostElementId */
function CostElementIdSetter() {
  const ctx = useDashboardContext();
  return (
    <div>
      <span data-testid="cost-element-id">
        {ctx.costElementId ?? "undefined"}
      </span>
      <button
        data-testid="set-ce"
        onClick={() => ctx.setCostElementId("ce-456")}
      />
    </div>
  );
}

describe("DashboardContextBus", () => {
  it("renders children", () => {
    renderWithTheme(
      <DashboardContextBus projectId="proj-1">
        <div data-testid="child">Hello Dashboard</div>
      </DashboardContextBus>,
    );
    expect(screen.getByTestId("child")).toHaveTextContent("Hello Dashboard");
  });

  it("exposes projectId from props", () => {
    renderWithTheme(
      <DashboardContextBus projectId="proj-42">
        <ContextReader />
      </DashboardContextBus>,
    );
    expect(screen.getByTestId("project-id")).toHaveTextContent("proj-42");
  });

  it("setWbeId updates context value", () => {
    renderWithTheme(
      <DashboardContextBus projectId="proj-1">
        <WbeIdSetter />
      </DashboardContextBus>,
    );

    expect(screen.getByTestId("wbe-id")).toHaveTextContent("undefined");

    act(() => {
      screen.getByTestId("set-wbe").click();
    });

    expect(screen.getByTestId("wbe-id")).toHaveTextContent("wbe-123");
  });

  it("setCostElementId updates context value", () => {
    renderWithTheme(
      <DashboardContextBus projectId="proj-1">
        <CostElementIdSetter />
      </DashboardContextBus>,
    );

    expect(screen.getByTestId("cost-element-id")).toHaveTextContent(
      "undefined",
    );

    act(() => {
      screen.getByTestId("set-ce").click();
    });

    expect(screen.getByTestId("cost-element-id")).toHaveTextContent("ce-456");
  });

  it("re-exposes TimeMachine values (asOf, branch, mode)", () => {
    renderWithTheme(
      <DashboardContextBus projectId="proj-1">
        <ContextReader />
      </DashboardContextBus>,
    );
    expect(screen.getByTestId("branch")).toHaveTextContent("main");
    expect(screen.getByTestId("mode")).toHaveTextContent("merged");
    expect(screen.getByTestId("as-of")).toHaveTextContent("undefined");
  });
});

describe("useDashboardContext", () => {
  it("throws a descriptive error when used outside DashboardContextBus", () => {
    // Suppress console.error for expected error
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    function OrphanConsumer() {
      useDashboardContext();
      return null;
    }

    expect(() => render(<OrphanConsumer />)).toThrow(
      "useDashboardContext must be used within DashboardContextBus",
    );

    spy.mockRestore();
  });

  it("returns context value when used inside provider", () => {
    function Captor() {
      const ctx = useDashboardContext();
      return (
        <div>
          <span data-testid="captor-project-id">{ctx.projectId}</span>
          <span data-testid="captor-wbe-id">
            {ctx.wbeId ?? "undefined"}
          </span>
          <span data-testid="captor-ce-id">
            {ctx.costElementId ?? "undefined"}
          </span>
          <span data-testid="captor-branch">{ctx.branch}</span>
        </div>
      );
    }

    renderWithTheme(
      <DashboardContextBus projectId="proj-test">
        <Captor />
      </DashboardContextBus>,
    );

    expect(screen.getByTestId("captor-project-id")).toHaveTextContent(
      "proj-test",
    );
    expect(screen.getByTestId("captor-wbe-id")).toHaveTextContent("undefined");
    expect(screen.getByTestId("captor-ce-id")).toHaveTextContent("undefined");
    expect(screen.getByTestId("captor-branch")).toHaveTextContent("main");
  });
});
