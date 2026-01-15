import { renderHook } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useWorkflowInfo } from "./useWorkflowInfo";

describe("useWorkflowInfo", () => {
  it("create mode should return only Draft option", () => {
    // Arrange & Act
    const { result } = renderHook(() =>
      useWorkflowInfo(undefined, undefined, undefined, undefined)
    );

    // Assert
    expect(result.current.statusOptions).toEqual([
      { label: "Draft", value: "Draft" },
    ]);
    expect(result.current.isStatusDisabled).toBe(false);
    expect(result.current.isBranchLocked).toBe(false);
    expect(result.current.lockedBranchWarning).toBeNull();
  });

  it("edit mode should return available transitions", () => {
    // Arrange & Act
    const { result } = renderHook(() =>
      useWorkflowInfo(
        "Submitted for Approval",
        ["Under Review"],
        true,
        false
      )
    );

    // Assert
    expect(result.current.statusOptions).toEqual([
      { label: "Under Review", value: "Under Review" },
    ]);
    expect(result.current.isStatusDisabled).toBe(false);
  });

  it("should disable status when branch is locked", () => {
    // Arrange & Act
    const { result } = renderHook(() =>
      useWorkflowInfo("Under Review", ["Approved", "Rejected"], true, true)
    );

    // Assert
    expect(result.current.isStatusDisabled).toBe(true);
    expect(result.current.isBranchLocked).toBe(true);
    expect(result.current.lockedBranchWarning).toBe(
      "This change order is currently under review. The branch is locked and no modifications are allowed."
    );
  });

  it("should disable status when cannot edit", () => {
    // Arrange & Act
    const { result } = renderHook(() =>
      useWorkflowInfo("Under Review", ["Approved", "Rejected"], false, false)
    );

    // Assert
    expect(result.current.isStatusDisabled).toBe(true);
  });

  it("should handle empty transitions by keeping current status", () => {
    // Arrange & Act
    const { result } = renderHook(() =>
      useWorkflowInfo("Implemented", [], true, false)
    );

    // Assert
    expect(result.current.statusOptions).toEqual([
      { label: "Implemented", value: "Implemented" },
    ]);
  });

  it("should handle null values gracefully", () => {
    // Arrange & Act
    const { result } = renderHook(() =>
      useWorkflowInfo("Draft", null, null, null)
    );

    // Assert
    expect(result.current.statusOptions).toEqual([
      { label: "Draft", value: "Draft" },
    ]);
    expect(result.current.isStatusDisabled).toBe(false);
    expect(result.current.isBranchLocked).toBe(false);
  });
});
