import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorkflowStepper, WORKFLOW_STEPS, getStepIndex, type WorkflowStepKey } from "./WorkflowStepper";

describe("WorkflowStepper", () => {
  describe("WORKFLOW_STEPS constant", () => {
    it("should have 5 workflow steps", () => {
      expect(WORKFLOW_STEPS).toHaveLength(5);
    });

    it("should have correct step keys", () => {
      const keys = WORKFLOW_STEPS.map((s) => s.key);
      expect(keys).toEqual(["draft", "submitted", "under_review", "approved", "implemented"]);
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
      expect(getStepIndex("Draft")).toBe(0);
    });

    it("should return 1 for Submitted for Approval status", () => {
      expect(getStepIndex("Submitted for Approval")).toBe(1);
    });

    it("should return 2 for Under Review status", () => {
      expect(getStepIndex("Under Review")).toBe(2);
    });

    it("should return 3 for Approved status", () => {
      expect(getStepIndex("Approved")).toBe(3);
    });

    it("should return 4 for Implemented status", () => {
      expect(getStepIndex("Implemented")).toBe(4);
    });

    it("should return 0 for Rejected status (returns to Draft)", () => {
      expect(getStepIndex("Rejected")).toBe(0);
    });

    it("should return 0 for unknown status", () => {
      expect(getStepIndex("Unknown")).toBe(0);
    });
  });

  describe("WorkflowStepper component", () => {
    it("should render workflow stepper for Draft status", () => {
      render(<WorkflowStepper status="Draft" />);
      // Stepper should be visible (Steps component renders)
      const stepsContainer = document.querySelector(".ant-steps");
      expect(stepsContainer).toBeInTheDocument();
    });

    it("should render workflow stepper for Approved status", () => {
      render(<WorkflowStepper status="Approved" />);
      const stepsContainer = document.querySelector(".ant-steps");
      expect(stepsContainer).toBeInTheDocument();
    });

    it("should render workflow stepper for Implemented status", () => {
      render(<WorkflowStepper status="Implemented" />);
      const stepsContainer = document.querySelector(".ant-steps");
      expect(stepsContainer).toBeInTheDocument();
    });

    it("should handle processing status prop", () => {
      render(<WorkflowStepper status="Approved" processingStatus="Under Review" />);
      const stepsContainer = document.querySelector(".ant-steps");
      expect(stepsContainer).toBeInTheDocument();
    });
  });
});
