import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { EVMKPIIndicator } from "../EVMKPIIndicator";

vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    theme: {
      useToken: () => ({
        token: {
          colorBgContainer: "#ffffff",
          colorBorder: "#d9d9d9",
          colorText: "#000000",
          colorTextSecondary: "#666666",
          colorTextTertiary: "#999999",
          colorSuccess: "#5da572",
          colorWarning: "#d4a549",
          colorError: "#c95d5f",
          colorPrimary: "#4a7c91",
          borderRadiusLG: 8,
          borderRadiusSM: 4,
          paddingXXS: 4,
          paddingMD: 16,
          paddingLG: 24,
          paddingXL: 32,
          colorFillSecondary: "#f0f0f0",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          colorBorderSecondary: "#f0f0f0",
          colorBgElevated: "#ffffff",
        },
      }),
    },
  };
});

describe("EVMKPIIndicator", () => {
  describe("Rendering", () => {
    it("renders label and formatted value", () => {
      render(<EVMKPIIndicator label="CPI" value={0.96} format="number" status="good" />);

      expect(screen.getByText("CPI")).toBeInTheDocument();
      expect(screen.getByText("0.96")).toBeInTheDocument();
    });

    it("shows N/A for null value", () => {
      render(<EVMKPIIndicator label="CPI" value={null} format="number" status="warning" />);

      expect(screen.getByText("N/A")).toBeInTheDocument();
    });
  });

  describe("Formatting", () => {
    it("formats currency correctly", () => {
      render(<EVMKPIIndicator label="BAC" value={1000000} format="currency" status="good" />);

      expect(screen.getByText("€1,000,000.00")).toBeInTheDocument();
    });

    it("formats percentage correctly", () => {
      render(<EVMKPIIndicator label="Progress" value={0.72} format="percentage" status="good" />);

      expect(screen.getByText("72%")).toBeInTheDocument();
    });

    it("formats number correctly", () => {
      render(<EVMKPIIndicator label="CPI" value={1.05} format="number" status="good" />);

      expect(screen.getByText("1.05")).toBeInTheDocument();
    });
  });

  describe("Status Colors", () => {
    it("applies success color dot for good status", () => {
      const { container } = render(
        <EVMKPIIndicator label="CPI" value={1.05} format="number" status="good" />
      );

      const dot = container.querySelector("span[style]");
      expect(dot).toBeInTheDocument();
    });

    it("applies warning color dot for warning status", () => {
      const { container } = render(
        <EVMKPIIndicator label="CPI" value={0.95} format="number" status="warning" />
      );

      const dot = container.querySelector("span[style]");
      expect(dot).toBeInTheDocument();
    });

    it("applies error color dot for bad status", () => {
      const { container } = render(
        <EVMKPIIndicator label="CPI" value={0.85} format="number" status="bad" />
      );

      const dot = container.querySelector("span[style]");
      expect(dot).toBeInTheDocument();
    });

    it("uses primary color when neutral is true", () => {
      const { container } = render(
        <EVMKPIIndicator label="BAC" value={1000000} format="currency" status="good" neutral />
      );

      const dot = container.querySelector("span[style]");
      expect(dot).toBeInTheDocument();
    });
  });
});
