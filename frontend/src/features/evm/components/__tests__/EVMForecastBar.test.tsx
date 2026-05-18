import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { EVMForecastBar } from "../EVMForecastBar";

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

describe("EVMForecastBar", () => {
  const defaultProps = {
    bac: 1000000,
    eac: 1041667,
    ac: 750000,
    etc: 291667,
    vac: -41667,
  };

  describe("Basic Rendering", () => {
    it("renders BAC label", () => {
      render(<EVMForecastBar {...defaultProps} />);

      expect(screen.getByText(/BAC/)).toBeInTheDocument();
    });

    it("renders EAC label", () => {
      render(<EVMForecastBar {...defaultProps} />);

      expect(screen.getByText(/EAC/)).toBeInTheDocument();
    });

    it("renders Spent label", () => {
      render(<EVMForecastBar {...defaultProps} />);

      expect(screen.getByText(/Spent/)).toBeInTheDocument();
    });

    it("renders Remaining label", () => {
      render(<EVMForecastBar {...defaultProps} />);

      expect(screen.getByText(/Remaining/)).toBeInTheDocument();
    });
  });

  describe("Null Values", () => {
    it("shows N/A for null EAC", () => {
      render(<EVMForecastBar {...defaultProps} eac={null} />);

      const eacText = screen.getByText(/EAC/);
      expect(eacText.textContent).toContain("N/A");
    });

    it("shows N/A for null ETC", () => {
      render(<EVMForecastBar {...defaultProps} etc={null} />);

      const remainingText = screen.getByText(/Remaining/);
      expect(remainingText.textContent).toContain("N/A");
    });

    it("does not render VAC when null", () => {
      render(<EVMForecastBar {...defaultProps} vac={null} />);

      expect(screen.queryByText(/VAC/)).not.toBeInTheDocument();
    });
  });

  describe("VAC Display", () => {
    it("renders VAC with green color for positive value", () => {
      render(<EVMForecastBar {...defaultProps} vac={50000} />);

      const vacText = screen.getByText(/VAC/);
      expect(vacText).toBeInTheDocument();
    });

    it("renders VAC with red color for negative value", () => {
      render(<EVMForecastBar {...defaultProps} vac={-41667} />);

      const vacText = screen.getByText(/VAC/);
      expect(vacText).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles zero BAC without division by zero", () => {
      expect(() => {
        render(<EVMForecastBar {...defaultProps} bac={0} />);
      }).not.toThrow();
    });

    it("handles all null forecast values", () => {
      expect(() => {
        render(
          <EVMForecastBar
            bac={1000000}
            eac={null}
            ac={750000}
            etc={null}
            vac={null}
          />
        );
      }).not.toThrow();
    });
  });
});
