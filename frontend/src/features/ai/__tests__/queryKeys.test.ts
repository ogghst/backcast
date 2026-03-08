import { describe, it, expect } from "vitest";
import { queryKeys } from "@/api/queryKeys";

describe("AI Query Keys", () => {
  describe("queryKeys.ai structure", () => {
    it("should have ai section defined", () => {
      expect(queryKeys.ai).toBeDefined();
    });

    it("should have assistants section with all, list, and detail keys", () => {
      expect(queryKeys.ai.assistants).toBeDefined();
      expect(queryKeys.ai.assistants.all).toEqual(["ai", "assistants"]);
      expect(queryKeys.ai.assistants.list()).toEqual(["ai", "assistants", "list"]);
      expect(queryKeys.ai.assistants.detail("test-id")).toEqual(["ai", "assistants", "detail", "test-id"]);
    });
  });
});
