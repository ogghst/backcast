/**
 * CostRegistrationModal Component Tests
 *
 * Tests for the cost registration modal, including budget enforcement behavior:
 * - Hard block (modal.error) when enforce_budget is true and budget exceeded
 * - Soft warning (modal.confirm) when enforce_budget is false and budget exceeded
 * - Direct submission when within budget
 * - Threshold warning (modal.confirm) when over threshold but under budget
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { CostRegistrationModal } from "./CostRegistrationModal";

// Mock the API hooks
vi.mock("../api/useCostRegistrations", () => ({
  useBudgetStatus: vi.fn(),
  useProjectBudgetSettings: vi.fn(),
}));

// Mock TimeMachineContext
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
  }),
}));

// Mock App.useApp to provide spyable modal.error and modal.confirm
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    App: {
      ...actual.App,
      useApp: () => ({
        message: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
        notification: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
        modal: {
          info: vi.fn(),
          success: vi.fn(),
          error: modalErrorSpy,
          warning: vi.fn(),
          confirm: modalConfirmSpy,
        },
      }),
    },
  };
});

import {
  useBudgetStatus,
  useProjectBudgetSettings,
} from "../api/useCostRegistrations";

const mockUseBudgetStatus = vi.mocked(useBudgetStatus);
const mockUseProjectBudgetSettings = vi.mocked(useProjectBudgetSettings);

// These are declared at module scope so the mock factory above can reference them.
// They are re-initialised in beforeEach().
let modalErrorSpy: ReturnType<typeof vi.fn>;
let modalConfirmSpy: ReturnType<typeof vi.fn>;

/** Helper: build budget status mock return */
const budgetStatusMock = (budget: number, used: number) => ({
  data: {
    cost_element_id: "ce-1",
    budget: String(budget),
    used: String(used),
    remaining: String(budget - used),
    percentage: budget > 0 ? (used / budget) * 100 : 0,
  },
  isLoading: false,
  isError: false,
  error: null,
  isSuccess: true,
});

/** Helper: build project budget settings mock return */
const budgetSettingsMock = (enforceBudget: boolean, threshold = 80) => ({
  data: {
    id: "settings-1",
    project_budget_settings_id: "pbs-1",
    project_id: "project-1",
    created_by: "user-1",
    warning_threshold_percent: String(threshold),
    allow_project_admin_override: true,
    enforce_budget: enforceBudget,
  },
  isLoading: false,
  isError: false,
  error: null,
  isSuccess: true,
});

describe("CostRegistrationModal", () => {
  let queryClient: QueryClient;
  let mockOnOk: ReturnType<typeof vi.fn>;
  let mockOnCancel: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    mockOnOk = vi.fn();
    mockOnCancel = vi.fn();
    modalErrorSpy = vi.fn();
    modalConfirmSpy = vi.fn();

    // Default mocks: no budget data, no enforcement
    mockUseBudgetStatus.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBudgetStatus>);

    mockUseProjectBudgetSettings.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useProjectBudgetSettings>);
  });

  /**
   * Renders the modal wrapped in TanStack Query provider.
   * App.useApp is mocked at module level to return our spy functions.
   */
  const renderModal = (
    props?: Partial<React.ComponentProps<typeof CostRegistrationModal>>,
  ) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <CostRegistrationModal
          open={true}
          onCancel={mockOnCancel}
          onOk={mockOnOk}
          confirmLoading={false}
          costElementId="ce-1"
          projectId="project-1"
          {...props}
        />
      </QueryClientProvider>,
    );
  };

  /**
   * Set the amount in the form by finding the Ant Design InputNumber's
   * native input element and firing a change event. Then click the
   * Create/Save button to trigger handleSubmit.
   */
  const setAmountAndSubmit = async (amountValue: number) => {
    const amountInput = document.querySelector(
      'input.ant-input-number-input',
    ) as HTMLInputElement;
    expect(amountInput).toBeTruthy();

    // Use React's internal value setter to bypass React's controlled input
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      'value',
    )?.set;
    nativeInputValueSetter?.call(amountInput, String(amountValue));
    fireEvent.change(amountInput, { target: { value: String(amountValue) } });

    // Find and click the modal OK button (triggers handleSubmit)
    const okButton = screen.getByRole("button", { name: /create|save/i });
    fireEvent.click(okButton);
  };

  // -------------------------------------------------------------------
  // Test: modal.error when enforce_budget=true and budget exceeded
  // -------------------------------------------------------------------
  it("shows error dialog when enforce_budget is true and budget exceeded", async () => {
    mockUseBudgetStatus.mockReturnValue(
      budgetStatusMock(1000, 0) as ReturnType<typeof useBudgetStatus>,
    );
    mockUseProjectBudgetSettings.mockReturnValue(
      budgetSettingsMock(true) as ReturnType<typeof useProjectBudgetSettings>,
    );

    renderModal();

    // Wait for the modal to render
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create/i })).toBeInTheDocument();
    });

    // Amount of 1500 exceeds budget of 1000
    await setAmountAndSubmit(1500);

    await waitFor(() => {
      expect(modalErrorSpy).toHaveBeenCalledTimes(1);
    });

    const errorCall = modalErrorSpy.mock.calls[0][0] as { title: string };
    expect(errorCall.title).toBe("Budget Limit Reached");

    expect(modalConfirmSpy).not.toHaveBeenCalled();
    expect(mockOnOk).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------
  // Test: modal.confirm when enforce_budget=false and budget exceeded
  // -------------------------------------------------------------------
  it("shows confirmation dialog when enforce_budget is false and budget exceeded", async () => {
    mockUseBudgetStatus.mockReturnValue(
      budgetStatusMock(1000, 0) as ReturnType<typeof useBudgetStatus>,
    );
    mockUseProjectBudgetSettings.mockReturnValue(
      budgetSettingsMock(false) as ReturnType<typeof useProjectBudgetSettings>,
    );

    renderModal();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create/i })).toBeInTheDocument();
    });

    await setAmountAndSubmit(1500);

    await waitFor(() => {
      expect(modalConfirmSpy).toHaveBeenCalledTimes(1);
    });

    const confirmCall = modalConfirmSpy.mock.calls[0][0] as { title: string };
    expect(confirmCall.title).toBe("Cost Element Budget Exceeded");

    expect(modalErrorSpy).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------
  // Test: direct submission when enforce_budget=true but within budget
  // -------------------------------------------------------------------
  it("allows submission when enforce_budget is true and within budget", async () => {
    mockUseBudgetStatus.mockReturnValue(
      budgetStatusMock(1000, 0) as ReturnType<typeof useBudgetStatus>,
    );
    mockUseProjectBudgetSettings.mockReturnValue(
      budgetSettingsMock(true) as ReturnType<typeof useProjectBudgetSettings>,
    );

    renderModal();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create/i })).toBeInTheDocument();
    });

    // Amount of 500 is well within budget of 1000
    await setAmountAndSubmit(500);

    await waitFor(() => {
      expect(mockOnOk).toHaveBeenCalledTimes(1);
    });

    expect(modalErrorSpy).not.toHaveBeenCalled();
    expect(modalConfirmSpy).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------
  // Test: threshold warning when enforce_budget=true, over threshold but under budget
  // -------------------------------------------------------------------
  it("shows confirmation dialog when enforce_budget is true and threshold exceeded but not budget", async () => {
    // Budget: 1000, Used: 0, Threshold: 80% -> warning limit = 800
    mockUseBudgetStatus.mockReturnValue(
      budgetStatusMock(1000, 0) as ReturnType<typeof useBudgetStatus>,
    );
    mockUseProjectBudgetSettings.mockReturnValue(
      budgetSettingsMock(true, 80) as ReturnType<typeof useProjectBudgetSettings>,
    );

    renderModal();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create/i })).toBeInTheDocument();
    });

    // Amount of 850 is 85% of budget (> 80% threshold) but under 1000 budget
    await setAmountAndSubmit(850);

    await waitFor(() => {
      expect(modalConfirmSpy).toHaveBeenCalledTimes(1);
    });

    const confirmCall = modalConfirmSpy.mock.calls[0][0] as { title: string };
    expect(confirmCall.title).toBe("Cost Element Budget Warning");

    expect(modalErrorSpy).not.toHaveBeenCalled();
  });
});
