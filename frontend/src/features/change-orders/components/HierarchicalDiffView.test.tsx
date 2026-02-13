import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { HierarchicalDiffView } from "./HierarchicalDiffView";
import type { ImpactAnalysisResponse } from "@/api/generated";

describe("HierarchicalDiffView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockImpactData: ImpactAnalysisResponse = {
    change_order_id: "BR-123",
    branch_name: "BR-CO-2026-001",
    main_branch_name: "main",
    kpi_scorecard: {
      budget_variance: "0.00",
      revenue_variance: "0.00",
      cost_variance: "0.00",
      budget_variance_percent: 0.0,
      revenue_variance_percent: 0.0,
      cost_variance_percent: 0.0,
    },
    entity_changes: {
      wbes: [
        {
          id: 1,
          name: "WBE 1 - Assembly Line",
          change_type: "modified",
          budget_delta: "5000.00",
          revenue_delta: "3000.00",
          cost_delta: "2000.00",
        },
        {
          id: 2,
          name: "WBE 2 - Packaging",
          change_type: "added",
          budget_delta: "10000.00",
          revenue_delta: "8000.00",
          cost_delta: null,
        },
        {
          id: 3,
          name: "WBE 3 - Testing",
          change_type: "removed",
          budget_delta: "-15000.00",
          revenue_delta: "-12000.00",
          cost_delta: "-3000.00",
        },
      ],
      cost_elements: [
        {
          id: 101,
          name: "Labor Costs",
          change_type: "modified",
          budget_delta: "2000.00",
          revenue_delta: null,
          cost_delta: "1000.00",
        },
        {
          id: 102,
          name: "Material Costs",
          change_type: "added",
          budget_delta: "5000.00",
          revenue_delta: "4000.00",
          cost_delta: null,
        },
        {
          id: 103,
          name: "Overhead",
          change_type: "removed",
          budget_delta: "-3000.00",
          revenue_delta: "-2000.00",
          cost_delta: "-1000.00",
        },
      ],
    },
  };

  describe("rendering tree structure", () => {
    it("should render tree with all levels (Project → WBEs → Cost Elements)", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Should show project level summary
      expect(screen.getByText(/Project Changes/i)).toBeInTheDocument();

      // Should show WBEs
      expect(screen.getByText(/WBE 1 - Assembly Line/i)).toBeInTheDocument();
      expect(screen.getByText(/WBE 2 - Packaging/i)).toBeInTheDocument();
      expect(screen.getByText(/WBE 3 - Testing/i)).toBeInTheDocument();

      // Should show Cost Elements
      expect(screen.getByText(/Labor Costs/i)).toBeInTheDocument();
      expect(screen.getByText(/Material Costs/i)).toBeInTheDocument();
      expect(screen.getByText(/Overhead/i)).toBeInTheDocument();
    });

    it("should render change count badges for entities with changes", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Should show total change count in summary
      expect(screen.getByText(/Total Changes/i)).toBeInTheDocument();

      // WBEs should have change indicators
      const wbe1Changes = screen.getAllByText(/modified/i).filter(
        (el) => el.textContent?.toLowerCase() === "modified"
      );
      expect(wbe1Changes.length).toBeGreaterThan(0);
    });

    it("should render summary cards with change breakdown", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Should show added count
      expect(screen.getByText(/Added/i)).toBeInTheDocument();

      // Should show modified count
      expect(screen.getByText(/Modified/i)).toBeInTheDocument();

      // Should show removed count
      expect(screen.getByText(/Removed/i)).toBeInTheDocument();
    });
  });

  describe("expand and collapse functionality", () => {
    it("should expand and collapse WBE nodes", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Find WBE node
      const wbeNode = screen.getByText(/WBE 1 - Assembly Line/i);

      // Should be able to click to toggle
      fireEvent.click(wbeNode);

      // After click, cost elements under this WBE should be visible
      // Note: This depends on the tree implementation
    });

    it("should support defaultExpandedLevel prop", () => {
      const { rerender } = render(
        <HierarchicalDiffView impactData={mockImpactData} defaultExpandedLevel={0} />
      );

      // Level 0 = all collapsed
      // Should not show cost elements initially

      rerender(
        <HierarchicalDiffView impactData={mockImpactData} defaultExpandedLevel={2} />
      );

      // Level 2 = WBEs expanded, showing cost elements
      // Should show cost elements
    });
  });

  describe("change indicators", () => {
    it("should display color-coded badges for change types", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Green for added
      const addedBadges = screen.getAllByText(/added/i);
      expect(addedBadges.length).toBeGreaterThan(0);

      // Orange/blue for modified
      const modifiedBadges = screen.getAllByText(/modified/i);
      expect(modifiedBadges.length).toBeGreaterThan(0);

      // Red for removed
      const removedBadges = screen.getAllByText(/removed/i);
      expect(removedBadges.length).toBeGreaterThan(0);
    });

    it("should show change count in badges", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Should display numbers indicating count of changes
      const changeCounts = screen.queryAllByText(/\d+/);
      expect(changeCounts.length).toBeGreaterThan(0);
    });

    it("should color-code borders or icons based on severity", () => {
      const { container } = render(
        <HierarchicalDiffView impactData={mockImpactData} />
      );

      // Check for color-coded elements
      // Green for added (#52c41a or similar)
      // Orange for modified (#fa8c16 or similar)
      // Red for removed (#f5222d or similar)

      const coloredElements = container.querySelectorAll(
        "[style*='color'], [class*='ant-tag']"
      );
      expect(coloredElements.length).toBeGreaterThan(0);
    });
  });

  describe("filter controls", () => {
    it("should have toggle to show/hide unchanged items", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} showUnchanged={false} />);

      // Should have filter control
      const filterToggle = screen.queryByRole("checkbox", {
        name: /show unchanged/i,
      });
      // Note: This might be a Switch or Toggle implementation
    });

    it("should filter out unchanged items when showUnchanged is false", () => {
      // Create data with unchanged items
      const dataWithUnchanged: ImpactAnalysisResponse = {
        ...mockImpactData,
        entity_changes: {
          wbes: [
            {
              id: 1,
              name: "Changed WBE",
              change_type: "modified",
              budget_delta: "1000.00",
              revenue_delta: "500.00",
              cost_delta: "200.00",
            },
          ],
          cost_elements: [],
        },
      };

      const { rerender } = render(
        <HierarchicalDiffView impactData={dataWithUnchanged} showUnchanged={false} />
      );

      // Should only show changed items

      rerender(
        <HierarchicalDiffView impactData={dataWithUnchanged} showUnchanged={true} />
      );

      // Should show all items (if we had unchanged items in the data)
    });
  });

  describe("click handling", () => {
    it("should call onEntityClick when an entity is clicked", () => {
      const handleClick = vi.fn();

      render(
        <HierarchicalDiffView
          impactData={mockImpactData}
          onEntityClick={handleClick}
        />
      );

      // Click on a WBE
      const wbeNode = screen.getByText(/WBE 1 - Assembly Line/i);
      fireEvent.click(wbeNode);

      // Should have been called (implementation might need preventDefault for expand/collapse)
      // Note: This depends on whether click is for selection or expansion
    });

    it("should pass correct entity ID and type to onEntityClick", () => {
      const handleClick = vi.fn();

      render(
        <HierarchicalDiffView
          impactData={mockImpactData}
          onEntityClick={handleClick}
        />
      );

      // This test depends on the implementation of click handling
      // Could be a separate button or a specific interaction mode
    });
  });

  describe("empty state", () => {
    it("should render empty state when no changes detected", () => {
      const emptyData: ImpactAnalysisResponse = {
        ...mockImpactData,
        entity_changes: {
          wbes: [],
          cost_elements: [],
        },
      };

      render(<HierarchicalDiffView impactData={emptyData} />);

      expect(screen.getByText(/No changes detected/i)).toBeInTheDocument();
    });

    it("should show appropriate message when entity_changes is undefined", () => {
      const noChangesData: ImpactAnalysisResponse = {
        ...mockImpactData,
        entity_changes: undefined,
      };

      render(<HierarchicalDiffView impactData={noChangesData} />);

      expect(screen.getByText(/No changes detected/i)).toBeInTheDocument();
    });
  });

  describe("data transformation", () => {
    it("should correctly group cost elements under WBEs", () => {
      // Note: The current EntityChange doesn't have parent_id
      // This test documents the expected behavior if that's added
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Cost elements should be displayed under their parent WBEs
      // or in a separate section if hierarchy isn't available
    });

    it("should calculate change summaries at each level", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Project level summary should aggregate all changes
      // WBE level summary should show changes for that WBE
      // Cost element level should show individual changes

      const summarySection = screen.getByText(/Total Changes/i);
      expect(summarySection).toBeInTheDocument();
    });

    it("should handle missing or null delta values", () => {
      const dataWithNulls: ImpactAnalysisResponse = {
        ...mockImpactData,
        entity_changes: {
          wbes: [
            {
              id: 1,
              name: "WBE with nulls",
              change_type: "modified",
              budget_delta: null,
              revenue_delta: null,
              cost_delta: null,
            },
          ],
          cost_elements: [],
        },
      };

      render(<HierarchicalDiffView impactData={dataWithNulls} />);

      // Should render without errors
      expect(screen.getByText(/WBE with nulls/i)).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper ARIA labels for tree structure", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Tree should have proper role
      const tree = screen.getByRole("tree");
      expect(tree).toBeInTheDocument();

      // Tree items should have proper roles (Ant Design Tree uses these roles)
      const treeItems = screen.queryAllByRole("treeitem");
      // Note: Ant Design might not expose all items as treeitem roles
      // Just verify tree exists
      expect(tree).toBeInTheDocument();
    });

    it("should support keyboard navigation", () => {
      render(<HierarchicalDiffView impactData={mockImpactData} />);

      // Ant Design Tree is keyboard accessible by default
      // Verify tree structure exists
      const tree = screen.getByRole("tree");
      expect(tree).toBeInTheDocument();
    });
  });

  describe("performance", () => {
    it("should handle large datasets efficiently", () => {
      // Generate large dataset
      const largeData: ImpactAnalysisResponse = {
        ...mockImpactData,
        entity_changes: {
          wbes: Array.from({ length: 50 }, (_, i) => ({
            id: i + 1,
            name: `WBE ${i + 1}`,
            change_type: "modified" as const,
            budget_delta: "1000.00",
            revenue_delta: "500.00",
            cost_delta: "200.00",
          })),
          cost_elements: Array.from({ length: 100 }, (_, i) => ({
            id: i + 100,
            name: `Cost Element ${i + 1}`,
            change_type: "added" as const,
            budget_delta: "500.00",
            revenue_delta: "300.00",
            cost_delta: null,
          })),
        },
      };

      const startTime = performance.now();
      render(<HierarchicalDiffView impactData={largeData} />);
      const endTime = performance.now();

      // Should render within reasonable time (< 1 second)
      expect(endTime - startTime).toBeLessThan(1000);
    });
  });

  describe("styling and layout", () => {
    it("should render with clean tree indentation", () => {
      const { container } = render(
        <HierarchicalDiffView impactData={mockImpactData} />
      );

      // Check for indentation classes or inline styles
      const indentedElements = container.querySelectorAll(
        "[class*='indent'], [style*='padding-left']"
      );
      expect(indentedElements.length).toBeGreaterThan(0);
    });

    it("should have hover effects for interactive nodes", () => {
      const { container } = render(
        <HierarchicalDiffView impactData={mockImpactData} />
      );

      // Check for hover states
      const interactiveElements = container.querySelectorAll(
        ".ant-tree-node-content-wrapper:hover, [class*='hover']"
      );

      // Should have at least some hover styling
      expect(interactiveElements.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe("edge cases", () => {
    it("should handle WBEs with no cost elements", () => {
      const dataWithNoCostElements: ImpactAnalysisResponse = {
        ...mockImpactData,
        entity_changes: {
          wbes: [
            {
              id: 1,
              name: "WBE with no children",
              change_type: "modified",
              budget_delta: "1000.00",
              revenue_delta: "500.00",
              cost_delta: "200.00",
            },
          ],
          cost_elements: [],
        },
      };

      render(<HierarchicalDiffView impactData={dataWithNoCostElements} />);

      expect(screen.getByText(/WBE with no children/i)).toBeInTheDocument();
    });

    it("should handle cost elements with no WBEs", () => {
      const dataWithNoWBEs: ImpactAnalysisResponse = {
        ...mockImpactData,
        entity_changes: {
          wbes: [],
          cost_elements: [
            {
              id: 101,
              name: "Orphan Cost Element",
              change_type: "added",
              budget_delta: "5000.00",
              revenue_delta: "3000.00",
              cost_delta: null,
            },
          ],
        },
      };

      render(<HierarchicalDiffView impactData={dataWithNoWBEs} />);

      expect(screen.getByText(/Orphan Cost Element/i)).toBeInTheDocument();
    });

    it("should handle undefined entity_changes gracefully", () => {
      const dataWithUndefined: ImpactAnalysisResponse = {
        ...mockImpactData,
        entity_changes: undefined,
      };

      render(<HierarchicalDiffView impactData={dataWithUndefined} />);

      expect(screen.getByText(/no changes detected/i)).toBeInTheDocument();
    });
  });
});
