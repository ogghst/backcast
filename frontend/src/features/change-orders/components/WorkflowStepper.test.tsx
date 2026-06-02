import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { WorkflowStepper } from "./WorkflowStepper";
import { WORKFLOW_STEPS, getStepIndex } from "./WorkflowConstants";

describe("WorkflowStepper", () => {
  describe("WORKFLOW_STEPS constant", () => {
    it("should have 5 workflow steps", () => {
      expect(WORKFLOW_STEPS).toHaveLength(5);
    });

    it("should have correct step keys", () => {
      const keys = WORKFLOW_STEPS.map((s) => s.key);
      expect(keys).toEqual([
        "draft",
        "submitted",
        "under_review",
        "approved",
        "implemented",
      ]);
    });

    it("should have correct step titles", () => {
      const titles = WORKFLOW_STEPS.map((s) => s.title);
      expect(titles).toContain("Draft");
      expect(titles).toContain("Submitted");
      expect(titles).toContain("In Review");
      expect(titles).toContain("Approved");
      expect(titles).toContain("Implemented");
    });
  });

  describe("getStepIndex", () => {
    it("should return 0 for Draft status", () => {
      expect(getStepIndex("draft")).toBe(0);
    });

    it("should return 1 for Submitted for Approval status", () => {
      expect(getStepIndex("submitted_for_approval")).toBe(1);
    });

    it("should return 2 for Under Review status", () => {
      expect(getStepIndex("under_review")).toBe(2);
    });

    it("should return 3 for Approved status", () => {
      expect(getStepIndex("approved")).toBe(3);
    });

    it("should return 4 for Implemented status", () => {
      expect(getStepIndex("implemented")).toBe(4);
    });

    it("should return 0 for Rejected status (returns to Draft)", () => {
      expect(getStepIndex("rejected")).toBe(0);
    });

    it("should return 0 for unknown status", () => {
      expect(getStepIndex("Unknown")).toBe(0);
    });
  });

  describe("WorkflowStepper component", () => {
    it("should render workflow stepper for Draft status", () => {
      render(<WorkflowStepper status="draft" />);
      // Stepper should be visible (Steps component renders)
      const stepsContainer = document.querySelector(".ant-steps");
      expect(stepsContainer).toBeInTheDocument();
    });

    it("should render workflow stepper for Approved status", () => {
      render(<WorkflowStepper status="approved" />);
      const stepsContainer = document.querySelector(".ant-steps");
      expect(stepsContainer).toBeInTheDocument();
    });

    it("should render workflow stepper for Implemented status", () => {
      render(<WorkflowStepper status="implemented" />);
      const stepsContainer = document.querySelector(".ant-steps");
      expect(stepsContainer).toBeInTheDocument();
    });

    it("should handle processing status prop", () => {
      render(
        <WorkflowStepper status="approved" processingStatus="in review" />,
      );
      const stepsContainer = document.querySelector(".ant-steps");
      expect(stepsContainer).toBeInTheDocument();
    });
  });
});
