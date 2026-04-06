import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { WidgetShell } from "./WidgetShell";
import {
  WidgetInteractionContext,
  type InteractionMode,
} from "./WidgetInteractionContext";

function renderWithTheme(
  ui: React.ReactElement,
  interactionValue?: {
    getInteraction: (id: string) => InteractionMode | null;
    setInteraction: (id: string, mode: InteractionMode) => void;
    clearInteraction: () => void;
    activeInteraction: {
      instanceId: string;
      mode: InteractionMode;
    } | null;
  },
) {
  const defaultInteractionValue = {
    getInteraction: () => null,
    setInteraction: vi.fn(),
    clearInteraction: vi.fn(),
    activeInteraction: null as {
      instanceId: string;
      mode: InteractionMode;
    } | null,
  };
  return render(
    <ConfigProvider>
      <WidgetInteractionContext.Provider
        value={interactionValue ?? defaultInteractionValue}
      >
        {ui}
      </WidgetInteractionContext.Provider>
    </ConfigProvider>,
  );
}

/** Find a button that contains the given Ant Design icon class */
function findIconButton(container: HTMLElement, iconClass: string) {
  return container.querySelector(`button .${iconClass}`);
}

/** Opens the toolbar by clicking the trigger icon */
function openToolbar() {
  const trigger = document.querySelector(
    "button[aria-label]",
  ) as HTMLButtonElement;
  if (trigger) fireEvent.click(trigger);
}

describe("WidgetShell", () => {
  const defaultProps = {
    instanceId: "test-1",
    title: "Test Widget",
    isEditing: false,
    onRemove: vi.fn(),
    children: <div data-testid="widget-content">Widget Content</div>,
  };

  it("renders children content", () => {
    renderWithTheme(<WidgetShell {...defaultProps} />);
    expect(screen.getByTestId("widget-content")).toBeInTheDocument();
  });

  it("renders trigger icon with aria-label in view mode", () => {
    renderWithTheme(<WidgetShell {...defaultProps} />);
    const trigger = document.querySelector(
      'button[aria-label="Test Widget"]',
    );
    expect(trigger).toBeInTheDocument();
  });

  it("does not render trigger icon in edit mode", () => {
    renderWithTheme(<WidgetShell {...defaultProps} isEditing={true} />);
    const trigger = document.querySelector('button[aria-label="Test Widget"]');
    expect(trigger).not.toBeInTheDocument();
  });

  it("shows title label by default and hides it when toolbar is open", () => {
    renderWithTheme(<WidgetShell {...defaultProps} />);
    // Title label is visible initially
    expect(screen.getByText("Test Widget")).toBeInTheDocument();

    // Open toolbar - title label hides, but toolbar shows title in its content
    openToolbar();
    expect(screen.getByText("Test Widget")).toBeInTheDocument();
  });

  it("does not show drag handle class by default in edit mode", () => {
    renderWithTheme(<WidgetShell {...defaultProps} isEditing={true} />);
    const handle = document.querySelector(".react-grid-drag-handle");
    expect(handle).not.toBeInTheDocument();
  });

  it("shows drag handle on Move button when interaction mode is move", () => {
    renderWithTheme(<WidgetShell {...defaultProps} isEditing={true} />, {
      getInteraction: (id) => (id === "test-1" ? "move" : null),
      setInteraction: vi.fn(),
      clearInteraction: vi.fn(),
      activeInteraction: {
        instanceId: "test-1",
        mode: "move" as InteractionMode,
      },
    });
    const handle = document.querySelector(".react-grid-drag-handle");
    expect(handle).toBeInTheDocument();
  });

  it("hides drag handle when not editing", () => {
    renderWithTheme(<WidgetShell {...defaultProps} isEditing={false} />);
    const handle = document.querySelector(".react-grid-drag-handle");
    expect(handle).not.toBeInTheDocument();
  });

  it("shows Move and Resize icon buttons in edit mode", () => {
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} isEditing={true} />,
    );
    expect(findIconButton(container, "anticon-drag")).toBeInTheDocument();
    expect(
      findIconButton(container, "anticon-column-width"),
    ).toBeInTheDocument();
  });

  it("Move button calls setInteraction with move mode", () => {
    const setInteraction = vi.fn();
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} isEditing={true} />,
      {
        getInteraction: () => null,
        setInteraction,
        clearInteraction: vi.fn(),
        activeInteraction: null,
      },
    );
    const moveBtn = findIconButton(container, "anticon-drag")!.closest(
      "button",
    )!;
    fireEvent.click(moveBtn);
    expect(setInteraction).toHaveBeenCalledWith("test-1", "move");
  });

  it("Resize button calls setInteraction with resize mode", () => {
    const setInteraction = vi.fn();
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} isEditing={true} />,
      {
        getInteraction: () => null,
        setInteraction,
        clearInteraction: vi.fn(),
        activeInteraction: null,
      },
    );
    const resizeBtn = findIconButton(container, "anticon-column-width")!.closest(
      "button",
    )!;
    fireEvent.click(resizeBtn);
    expect(setInteraction).toHaveBeenCalledWith("test-1", "resize");
  });

  it("Move button calls clear when already in move mode", () => {
    const clearInteraction = vi.fn();
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} isEditing={true} />,
      {
        getInteraction: (id) => (id === "test-1" ? "move" : null),
        setInteraction: vi.fn(),
        clearInteraction,
        activeInteraction: {
          instanceId: "test-1",
          mode: "move" as InteractionMode,
        },
      },
    );
    const moveBtn = findIconButton(container, "anticon-drag")!.closest(
      "button",
    )!;
    fireEvent.click(moveBtn);
    expect(clearInteraction).toHaveBeenCalled();
  });

  it("shows delete icon button in edit mode action bar directly", () => {
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} isEditing={true} />,
    );
    // No need to open toolbar - delete is in the persistent edit bar
    expect(findIconButton(container, "anticon-delete")).toBeInTheDocument();
  });

  it("hides delete button when not editing", () => {
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} isEditing={false} />,
    );
    // No need to open toolbar - delete should never appear in view mode
    expect(
      findIconButton(container, "anticon-delete"),
    ).not.toBeInTheDocument();
  });

  it("calls onRemove after two taps on delete button in edit mode", () => {
    const onRemove = vi.fn();
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} isEditing={true} onRemove={onRemove} />,
    );
    const btn = findIconButton(container, "anticon-delete")!.closest("button")!;

    // First tap — enters confirm state, does NOT remove
    fireEvent.click(btn);
    expect(onRemove).not.toHaveBeenCalled();

    // Second tap — confirms removal
    fireEvent.click(btn);
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it("toggles collapse state on collapse button click", () => {
    renderWithTheme(<WidgetShell {...defaultProps} />);
    // Content visible initially
    expect(screen.getByTestId("widget-content")).toBeInTheDocument();

    // Open toolbar to access collapse button
    openToolbar();

    // Click collapse button (down arrow)
    const collapseBtn = document.querySelector(
      "button .anticon-down",
    )?.closest("button");
    expect(collapseBtn).toBeTruthy();
    fireEvent.click(collapseBtn!);

    // Content should be hidden
    expect(screen.queryByTestId("widget-content")).not.toBeInTheDocument();
  });

  it("renders icon in trigger when provided", () => {
    renderWithTheme(
      <WidgetShell
        {...defaultProps}
        icon={<span data-testid="icon">📊</span>}
      />,
    );
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });

  it("shows refresh icon in toolbar when onRefresh is provided", () => {
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} onRefresh={vi.fn()} />,
    );
    openToolbar();
    expect(
      findIconButton(container, "anticon-reload"),
    ).toBeInTheDocument();
  });

  it("does not show refresh icon when onRefresh is not provided", () => {
    const { container } = renderWithTheme(<WidgetShell {...defaultProps} />);
    openToolbar();
    expect(
      findIconButton(container, "anticon-reload"),
    ).not.toBeInTheDocument();
  });

  it("shows loading skeleton when isLoading is true", () => {
    renderWithTheme(<WidgetShell {...defaultProps} isLoading={true} />);
    expect(screen.queryByTestId("widget-content")).not.toBeInTheDocument();
    expect(document.querySelector(".ant-skeleton")).toBeInTheDocument();
  });

  it("shows error message when error is provided", () => {
    renderWithTheme(
      <WidgetShell
        {...defaultProps}
        error={new Error("Test error")}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText("Test error")).toBeInTheDocument();
  });

  it("dismisses toolbar on click outside in view mode", () => {
    renderWithTheme(
      <div>
        <div data-testid="outside" />
        <WidgetShell {...defaultProps} />
      </div>,
    );

    // Open toolbar
    openToolbar();
    expect(screen.getByRole("toolbar")).toBeInTheDocument();

    // Click outside
    fireEvent.mouseDown(screen.getByTestId("outside"));
    expect(screen.queryByRole("toolbar")).not.toBeInTheDocument();
  });
});
