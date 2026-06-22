import { describe, it, expect } from "vitest";
import {
  projectNavItems,
  wbeNavItems,
  costElementNavItems,
  controlAccountNavItems,
  workPackageNavItems,
} from "./entityNavItems";

describe("entityNavItems", () => {
  describe("projectNavItems", () => {
    it("returns the project detail tabs (Explorer omitted, Overview is the index)", () => {
      const items = projectNavItems("p1");
      expect(items.map((i) => ({ key: i.key, label: i.label }))).toEqual([
        { key: "dashboard", label: "Dashboard" },
        { key: "overview", label: "Overview" },
        { key: "structure", label: "Structure" },
        { key: "schedule", label: "Schedule" },
        { key: "change-orders", label: "Change Orders" },
        { key: "members", label: "Members" },
        { key: "evm-analysis", label: "EVM Analysis" },
        { key: "coq-analysis", label: "COQ Analysis" },
        { key: "cost-events", label: "Cost Events" },
        { key: "documents", label: "Documents" },
        { key: "admin", label: "Admin" },
      ]);
    });

    it("builds paths off the projectId param", () => {
      const items = projectNavItems("p1");
      expect(items[0].path).toBe("/projects/p1/dashboard");
      expect(items[1].path).toBe("/projects/p1"); // index
      expect(items[items.length - 1].path).toBe("/projects/p1/admin");
      // No explorer entry.
      expect(items.find((i) => i.key === "explorer")).toBeUndefined();
    });
  });

  describe("wbeNavItems", () => {
    it("returns the WBS element tabs", () => {
      const items = wbeNavItems("p1", "w1");
      expect(items.map((i) => i.key)).toEqual([
        "overview",
        "evm-analysis",
        "cost-history",
        "documents",
      ]);
      expect(items[0].path).toBe("/projects/p1/wbs-elements/w1");
      expect(items[1].path).toBe(
        "/projects/p1/wbs-elements/w1/evm-analysis",
      );
      expect(items[3].path).toBe("/projects/p1/wbs-elements/w1/documents");
    });
  });

  describe("costElementNavItems", () => {
    it("returns the cost element tabs", () => {
      const items = costElementNavItems("c1");
      expect(items.map((i) => i.key)).toEqual([
        "overview",
        "cost-registrations",
        "cost-history",
        "documents",
      ]);
      expect(items[0].path).toBe("/cost-elements/c1");
      expect(items[1].path).toBe("/cost-elements/c1/cost-registrations");
    });
  });

  describe("controlAccountNavItems", () => {
    it("returns the control account tabs", () => {
      const items = controlAccountNavItems("p1", "ca1");
      expect(items.map((i) => i.key)).toEqual([
        "overview",
        "evm-analysis",
        "cost-history",
        "documents",
      ]);
      expect(items[0].path).toBe(
        "/projects/p1/control-accounts/ca1",
      );
      expect(items[1].path).toBe(
        "/projects/p1/control-accounts/ca1/evm-analysis",
      );
    });
  });

  describe("workPackageNavItems", () => {
    it("nests under project when projectId is provided", () => {
      const items = workPackageNavItems("wp1", "p1");
      expect(items.map((i) => i.key)).toEqual([
        "overview",
        "cost-registrations",
        "cost-history",
        "evm-analysis",
        "documents",
      ]);
      expect(items[0].path).toBe("/projects/p1/work-packages/wp1");
      expect(items[1].path).toBe(
        "/projects/p1/work-packages/wp1/cost-registrations",
      );
    });

    it("uses standalone path when projectId is omitted", () => {
      const items = workPackageNavItems("wp1");
      expect(items[0].path).toBe("/work-packages/wp1");
      expect(items[2].path).toBe("/work-packages/wp1/cost-history");
    });
  });

  describe("NavigationItem shape", () => {
    it("every item has a key, label, and path string", () => {
      const all = [
        ...projectNavItems("p"),
        ...wbeNavItems("p", "w"),
        ...costElementNavItems("c"),
        ...controlAccountNavItems("p", "ca"),
        ...workPackageNavItems("wp"),
        ...workPackageNavItems("wp", "p"),
      ];
      for (const item of all) {
        expect(typeof item.key).toBe("string");
        expect(typeof item.label).toBe("string");
        expect(typeof item.path).toBe("string");
        expect(item.path.startsWith("/")).toBe(true);
      }
    });
  });
});
