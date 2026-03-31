/**
 * Tests for LoadMoreButton component
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConfigProvider, theme } from "antd";
import { LoadMoreButton } from "../LoadMoreButton";

// Wrapper to provide Ant Design theme
const ThemeWrapper = ({ children }: { children: React.ReactNode }) => (
  <ConfigProvider theme={{ algorithm: theme.defaultAlgorithm }}>
    {children}
  </ConfigProvider>
);

describe("LoadMoreButton", () => {
  it("should render correctly", () => {
    render(
      <ThemeWrapper>
        <LoadMoreButton
          onLoadMore={vi.fn()}
          loading={false}
          disabled={false}
        />
      </ThemeWrapper>
    );

    expect(screen.getByText("Load More")).toBeInTheDocument();
  });

  it("should show loading state", () => {
    render(
      <ThemeWrapper>
        <LoadMoreButton
          onLoadMore={vi.fn()}
          loading={true}
          disabled={false}
        />
      </ThemeWrapper>
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("should be disabled when disabled prop is true", () => {
    render(
      <ThemeWrapper>
        <LoadMoreButton
          onLoadMore={vi.fn()}
          loading={false}
          disabled={true}
        />
      </ThemeWrapper>
    );

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  it("should be disabled when loading", () => {
    render(
      <ThemeWrapper>
        <LoadMoreButton
          onLoadMore={vi.fn()}
          loading={true}
          disabled={false}
        />
      </ThemeWrapper>
    );

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  it("should call onLoadMore when clicked", () => {
    const handleClick = vi.fn();
    render(
      <ThemeWrapper>
        <LoadMoreButton
          onLoadMore={handleClick}
          loading={false}
          disabled={false}
        />
      </ThemeWrapper>
    );

    const button = screen.getByRole("button");
    fireEvent.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("should not call onLoadMore when disabled", () => {
    const handleClick = vi.fn();
    render(
      <ThemeWrapper>
        <LoadMoreButton
          onLoadMore={handleClick}
          loading={false}
          disabled={true}
        />
      </ThemeWrapper>
    );

    const button = screen.getByRole("button");
    fireEvent.click(button);

    expect(handleClick).not.toHaveBeenCalled();
  });

  it("should not call onLoadMore when loading", () => {
    const handleClick = vi.fn();
    render(
      <ThemeWrapper>
        <LoadMoreButton
          onLoadMore={handleClick}
          loading={true}
          disabled={false}
        />
      </ThemeWrapper>
    );

    const button = screen.getByRole("button");
    fireEvent.click(button);

    expect(handleClick).not.toHaveBeenCalled();
  });
});
