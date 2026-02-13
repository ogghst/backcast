import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApprovalInfo } from "./ApprovalInfo";
import type { ApprovalInfoPublic as ApprovalInfoType } from "@/api/generated";

// Mock dayjs to have consistent date formatting
vi.mock("dayjs", () => ({
  default: (date: string) => ({
    format: (fmt: string) => {
      if (fmt === "MMM D, YYYY") {
        return "Feb 4, 2026";
      }
      return date;
    },
  }),
}));

const createMockQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const mockApprovalInfo: ApprovalInfoType = {
  impact_level: "HIGH",
  financial_impact: {
    budget_delta: -50000,
    revenue_delta: 25000,
  },
  assigned_approver: {
    user_id: "123",
    full_name: "John Doe",
    email: "john.doe@example.com",
    role: "Project Manager",
  },
  sla_assigned_at: "2026-02-01T00:00:00Z",
  sla_due_date: "2026-02-10T00:00:00Z",
  sla_status: "approaching",
  sla_business_days_remaining: 3,
  user_can_approve: false,
  user_authority_level: "MEDIUM",
};

describe("ApprovalInfo Component", () => {
  it("renders null when approvalInfo is null", () => {
    const { container } = render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={null} isLoading={false} />
      </QueryClientProvider>,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders null when impact_level is null", () => {
    const { container } = render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo
          approvalInfo={{
            ...mockApprovalInfo,
            impact_level: null,
          }}
          isLoading={false}
        />
      </QueryClientProvider>,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders impact level badge", () => {
    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={mockApprovalInfo} isLoading={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByText("High Impact")).toBeInTheDocument();
  });

  it("renders assigned approver details", () => {
    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={mockApprovalInfo} isLoading={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("john.doe@example.com")).toBeInTheDocument();
    expect(screen.getByText("Project Manager")).toBeInTheDocument();
  });

  it("renders SLA information", () => {
    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={mockApprovalInfo} isLoading={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByText("3 business days")).toBeInTheDocument();
    expect(screen.getByText("Deadline Approaching")).toBeInTheDocument();
  });

  it("renders financial impact", () => {
    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={mockApprovalInfo} isLoading={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByText(/-\$50,000/)).toBeInTheDocument();
    expect(screen.getByText(/\+\$25,000/)).toBeInTheDocument();
  });

  it("renders user authority level", () => {
    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={mockApprovalInfo} isLoading={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Cannot Approve")).toBeInTheDocument();
    expect(screen.getByText(/\(Your level: MEDIUM\)/)).toBeInTheDocument();
  });

  it("shows loading state", () => {
    const { container } = render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={mockApprovalInfo} isLoading={true} />
      </QueryClientProvider>,
    );

    // Card should be present with loading state
    const card = container.querySelector(".ant-card");
    expect(card).toBeInTheDocument();
    // Card should have loading class
    expect(card?.classList.contains("ant-card-loading")).toBe(true);
  });

  it("displays Can Approve when user has authority", () => {
    const approvalInfoWithAuthority = {
      ...mockApprovalInfo,
      user_can_approve: true,
    };

    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo
          approvalInfo={approvalInfoWithAuthority}
          isLoading={false}
        />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Can Approve")).toBeInTheDocument();
  });

  it("handles LOW impact level", () => {
    const lowImpactInfo = {
      ...mockApprovalInfo,
      impact_level: "LOW" as const,
    };

    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={lowImpactInfo} isLoading={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Low Impact")).toBeInTheDocument();
  });

  it("handles CRITICAL impact level", () => {
    const criticalImpactInfo = {
      ...mockApprovalInfo,
      impact_level: "CRITICAL" as const,
    };

    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={criticalImpactInfo} isLoading={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Critical Impact")).toBeInTheDocument();
  });

  it("handles overdue SLA status", () => {
    const overdueInfo = {
      ...mockApprovalInfo,
      sla_status: "overdue" as const,
    };

    render(
      <QueryClientProvider client={createMockQueryClient()}>
        <ApprovalInfo approvalInfo={overdueInfo} isLoading={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });
});
