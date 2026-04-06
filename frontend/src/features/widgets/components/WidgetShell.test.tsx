import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { WidgetShell } from "./WidgetShell";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
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

  it("renders drag handle in edit mode action bar", () => {
    renderWithTheme(<WidgetShell {...defaultProps} isEditing={true} />);
    const handle = document.querySelector(".react-grid-drag-handle");
    expect(handle).toBeInTheDocument();
  });

  it("hides drag handle when not editing", () => {
    renderWithTheme(<WidgetShell {...defaultProps} isEditing={false} />);
    const handle = document.querySelector(".react-grid-drag-handle");
    expect(handle).not.toBeInTheDocument();
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

  it("calls onRemove when Popconfirm is confirmed in edit mode", () => {
    const onRemove = vi.fn();
    const { container } = renderWithTheme(
      <WidgetShell {...defaultProps} isEditing={true} onRemove={onRemove} />,
    );
    // No need to open toolbar - delete button is in the persistent edit bar
    const btn = findIconButton(container, "anticon-delete")!.closest("button")!;
    fireEvent.click(btn);
    // Popconfirm opens - find and click the "Remove" button in the popover
    const popconfirmBtn = document.querySelector(
      '.ant-popconfirm .ant-btn-primary',
    ) as HTMLElement;
    expect(popconfirmBtn).toBeTruthy();
    fireEvent.click(popconfirmBtn);
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
