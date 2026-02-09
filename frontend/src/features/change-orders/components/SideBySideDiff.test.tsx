import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SideBySideDiff } from "./SideBySideDiff";

describe("SideBySideDiff", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockFieldLabels = {
    wbe_name: "WBE Name",
    budget: "Budget",
    description: "Description",
    justification: "Justification",
  };

  describe("rendering all change types", () => {
    it("should render added fields with green badge", () => {
      const mainData = { wbe_name: "Old Name" };
      const branchData = {
        wbe_name: "New Name",
        budget: "50000",
      };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
        />
      );

      // Check for added field badge
      const addedBadge = screen.getByText("Budget").parentElement?.querySelector(".ant-badge");
      expect(addedBadge).toBeInTheDocument();
    });

    it("should render modified fields with orange badge", () => {
      const mainData = { wbe_name: "Old Name", budget: "30000" };
      const branchData = { wbe_name: "New Name", budget: "50000" };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
        />
      );

      // Check that both values are shown for modified field
      expect(screen.getByText("Old Name")).toBeInTheDocument();
      expect(screen.getByText("New Name")).toBeInTheDocument();
    });

    it("should render removed fields with red badge", () => {
      const mainData = {
        wbe_name: "Old Name",
        budget: "30000",
        description: "This will be removed",
      };
      const branchData = { wbe_name: "New Name" };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
        />
      );

      // Check for removed field
      expect(screen.getByText("This will be removed")).toBeInTheDocument();
    });

    it("should not render unchanged fields when showing only changes", () => {
      const mainData = {
        wbe_name: "Same Name",
        budget: "30000",
        description: "Same description",
      };
      const branchData = {
        wbe_name: "Same Name",
        budget: "50000", // Modified
        description: "Same description",
      };

      const { container } = render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
          showUnchanged={false}
        />
      );

      // Unchanged field (description) should not be visible
      expect(screen.queryByText("Same description")).not.toBeInTheDocument();
      // Changed field (budget) should be visible
      expect(screen.getByText("30000")).toBeInTheDocument();
      expect(screen.getByText("50000")).toBeInTheDocument();
    });
  });

  describe("filter functionality", () => {
    it("should show only additions when filter is set to additions", () => {
      const mainData = { wbe_name: "Old Name", budget: "30000" };
      const branchData = {
        wbe_name: "New Name",
        budget: "50000",
        description: "New Description",
      };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
          showUnchanged={false}
        />
      );

      // Click additions filter
      const additionsFilter = screen.getByText(/additions/i);
      fireEvent.click(additionsFilter);

      // Should show description (added)
      expect(screen.getByText("New Description")).toBeInTheDocument();
      // Should not show modified fields
      expect(screen.queryByText("Old Name")).not.toBeInTheDocument();
    });

    it("should show only modifications when filter is set to modifications", () => {
      const mainData = { wbe_name: "Old Name", budget: "30000" };
      const branchData = {
        wbe_name: "New Name",
        budget: "50000",
        description: "New Description",
      };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
          showUnchanged={false}
        />
      );

      // Click modifications filter
      const modificationsFilter = screen.getByText(/modifications/i);
      fireEvent.click(modificationsFilter);

      // Should show modified fields
      expect(screen.getByText("Old Name")).toBeInTheDocument();
      expect(screen.getByText("New Name")).toBeInTheDocument();
      // Should not show added fields
      expect(screen.queryByText("New Description")).not.toBeInTheDocument();
    });

    it("should show only removals when filter is set to removals", () => {
      const mainData = {
        wbe_name: "Old Name",
        budget: "30000",
        description: "To be removed",
      };
      const branchData = { wbe_name: "New Name", budget: "50000" };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
          showUnchanged={false}
        />
      );

      // Click removals filter
      const removalsFilter = screen.getByText(/removals/i);
      fireEvent.click(removalsFilter);

      // Should show removed field
      expect(screen.getByText("To be removed")).toBeInTheDocument();
      // Should not show modified fields
      expect(screen.queryByText("New Name")).not.toBeInTheDocument();
    });
  });

  describe("text diff highlighting", () => {
    it("should show inline diff for long text fields (>50 chars)", () => {
      const longText =
        "This is a very long description that exceeds fifty characters and should trigger inline diff visualization";
      const modifiedLongText =
        "This is a very long description that exceeds fifty characters and should trigger inline changed diff visualization";

      const mainData = { description: longText };
      const branchData = { description: modifiedLongText };

      const { container } = render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
        />
      );

      // Check for diff highlighting elements
      const diffElements = container.querySelectorAll(".diff-added, .diff-removed");
      expect(diffElements.length).toBeGreaterThan(0);
    });

    it("should not show inline diff for short text fields", () => {
      const mainData = { wbe_name: "Short" };
      const branchData = { wbe_name: "New Short" };

      const { container } = render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
        />
      );

      // Should not have diff highlighting classes
      const diffElements = container.querySelectorAll(".diff-added, .diff-removed");
      expect(diffElements.length).toBe(0);
    });
  });

  describe("responsive layout", () => {
    it("should render two-column layout on desktop", () => {
      const mainData = { wbe_name: "Old Name" };
      const branchData = { wbe_name: "New Name" };

      const { container } = render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
        />
      );

      // Check for two-column layout classes
      const columns = container.querySelectorAll(".ant-col");
      expect(columns.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe("empty state", () => {
    it("should render empty state when no changes detected", () => {
      const mainData = { wbe_name: "Same", budget: "30000" };
      const branchData = { wbe_name: "Same", budget: "30000" };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
          showUnchanged={false}
        />
      );

      expect(screen.getByText(/no changes detected/i)).toBeInTheDocument();
    });

    it("should render excluded fields correctly", () => {
      const mainData = {
        wbe_name: "Name",
        budget: "30000",
        created_at: "2024-01-01",
      };
      const branchData = {
        wbe_name: "Name",
        budget: "50000",
        updated_at: "2024-01-02",
      };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
          excludeFields={["created_at", "updated_at"]}
        />
      );

      // Should not show excluded fields
      expect(screen.queryByText("2024-01-01")).not.toBeInTheDocument();
      expect(screen.queryByText("2024-01-02")).not.toBeInTheDocument();
    });
  });

  describe("edge cases", () => {
    it("should handle null and undefined values", () => {
      const mainData = {
        wbe_name: "Name",
        budget: null as unknown as string,
        description: undefined as unknown as string,
      };
      const branchData = {
        wbe_name: "Name",
        budget: "50000",
        description: "New Description",
      };

      render(
        <SideBySideDiff
          mainData={mainData}
          branchData={branchData}
          fieldLabels={mockFieldLabels}
        />
      );

      // Should render without errors
      expect(screen.getByText("Name")).toBeInTheDocument();
    });

    it("should handle empty objects", () => {
      render(
        <SideBySideDiff
          mainData={{}}
          branchData={{}}
          fieldLabels={mockFieldLabels}
        />
      );

      expect(screen.getByText(/no changes detected/i)).toBeInTheDocument();
    });
  });
});
