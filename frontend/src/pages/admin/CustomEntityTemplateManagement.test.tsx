import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { App } from "antd";

import { CustomEntityTemplateManagement } from "./CustomEntityTemplateManagement";
import type { CustomEntityTemplateRead } from "@/api/generated";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Allow-all auth store so all RBAC gates pass.
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: unknown) => {
    const mockState = {
      hasPermission: () => true,
      hasRole: () => true,
      hasAnyPermission: () => true,
      hasAllPermissions: () => true,
    };
    return typeof selector === "function" ? selector(mockState) : mockState;
  },
}));

const mockTemplates: CustomEntityTemplateRead[] = [
  {
    code: "CO_FIELDS",
    name: "Change Order Fields",
    description: null,
    target_entity_type: "CHANGE_ORDER",
    field_definitions: { reason: { type: "text", label: "Reason" } },
    id: "tmpl-1",
    custom_entity_template_id: "tmpl-1",
    organizational_unit_id: "ou-1",
    created_by: "user-1",
  },
];

vi.mock("@/features/custom-fields/api/useCustomEntityTemplates", () => ({
  useCustomEntityTemplates: () => ({ data: mockTemplates, isLoading: false }),
  useCustomEntityTemplateHistory: () => ({ data: [], isLoading: false }),
  useCreateCustomEntityTemplate: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateCustomEntityTemplate: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteCustomEntityTemplate: () => ({ mutate: vi.fn() }),
}));

vi.mock("@/features/organizational-units/hooks/useOrgUnitTree", () => ({
  useOrgUnitTree: () => ({
    items: [],
    treeData: [],
    flatMap: new Map(),
    pathMap: new Map([["ou-1", "Global"]]),
    isLoading: false,
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App>{children}</App>
      </QueryClientProvider>
    </BrowserRouter>
  );
};

describe("CustomEntityTemplateManagement", () => {
  beforeEach(() => {
    mockTemplates.length = 0;
    mockTemplates.push({
      code: "CO_FIELDS",
      name: "Change Order Fields",
      description: null,
      target_entity_type: "CHANGE_ORDER",
      field_definitions: { reason: { type: "text", label: "Reason" } },
      id: "tmpl-1",
      custom_entity_template_id: "tmpl-1",
      organizational_unit_id: "ou-1",
      created_by: "user-1",
    });
  });

  it("renders the page title and Add Template button", async () => {
    render(<CustomEntityTemplateManagement />, { wrapper: createWrapper() });
    expect(
      screen.getByText("Custom Entity Templates"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /add template/i }),
    ).toBeInTheDocument();
  });

  it("renders the template rows with target entity and field count", async () => {
    render(<CustomEntityTemplateManagement />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Change Order Fields")).toBeInTheDocument();
    });
    expect(screen.getByText("CO_FIELDS")).toBeInTheDocument();
    expect(screen.getByText("Change Order")).toBeInTheDocument();
    expect(screen.getByText("Global")).toBeInTheDocument();
    // Field count column renders a Tag with the field count. The data row is
    // the one containing the template code; its Tag with text "1" is the
    // field count (the code column renders a Tag too, but with "CO_FIELDS").
    const rows = screen.getAllByRole("row");
    const dataRow = rows.find((r) => r.textContent?.includes("CO_FIELDS"));
    const tagsInRow = dataRow?.querySelectorAll(".ant-tag") ?? [];
    const tagTexts = Array.from(tagsInRow).map((t) => t.textContent ?? "");
    expect(tagTexts).toContain("1");
  });
});
