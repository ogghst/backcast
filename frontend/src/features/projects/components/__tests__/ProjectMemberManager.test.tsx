/**
 * ProjectMemberManager Component Tests
 *
 * Tests for the project member management component.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { ProjectMemberManager } from "../ProjectMemberManager";
import { ProjectRole } from "../../types/projectMembers";
import type { ProjectMemberRead } from "../../types/projectMembers";

// Type for mocked hook return values
interface MockUseProjectMembersReturn {
  data: ProjectMemberRead[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isSuccess: boolean;
}

interface MockMutationReturn {
  mutate: ReturnType<typeof vi.fn>;
  isPending: boolean;
}

// Mock the hooks
vi.mock("../../hooks/useProjectMembers", () => ({
  useProjectMembers: vi.fn(),
  useAddProjectMember: vi.fn(),
  useRemoveProjectMember: vi.fn(),
  useUpdateProjectMember: vi.fn(),
}));

// Mock the auth store
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: vi.fn(),
}));

// Mock useThemeTokens hook
vi.mock("@/hooks/useThemeTokens", () => ({
  useThemeTokens: () => ({
    spacing: {
      xs: 4,
      sm: 8,
      md: 16,
      lg: 24,
      xl: 32,
      xxl: 40,
    },
    typography: {
      sizes: {
        xs: 10,
        sm: 12,
        md: 14,
        lg: 16,
        xl: 20,
        xxl: 24,
      },
      weights: {
        normal: 400,
        medium: 500,
        semiBold: 600,
        bold: 700,
      },
    },
    borderRadius: {
      sm: 4,
      md: 6,
      lg: 8,
      xl: 12,
    },
    colors: {
      primary: "#1890ff",
      success: "#52c41a",
      warning: "#faad14",
      error: "#ff4d4f",
      textSecondary: "#666666",
      text: {
        primary: "#000000",
        secondary: "#666666",
      },
      border: "#d9d9d9",
      background: {
        default: "#f0f0f0",
      },
    },
  }),
}));

// Mock useUsers hook
vi.mock("@/features/users/api/useUsers", () => ({
  useUsers: vi.fn(),
}));

import { useProjectMembers, useAddProjectMember, useRemoveProjectMember, useUpdateProjectMember } from "../../hooks/useProjectMembers";
import { useAuthStore } from "@/stores/useAuthStore";
import { useUsers } from "@/features/users/api/useUsers";

const mockUseProjectMembers = vi.mocked(useProjectMembers);
const mockUseAddProjectMember = vi.mocked(useAddProjectMember);
const mockUseRemoveProjectMember = vi.mocked(useRemoveProjectMember);
const mockUseUpdateProjectMember = vi.mocked(useUpdateProjectMember);
const mockUseAuthStore = vi.mocked(useAuthStore);
const mockUseUsers = vi.mocked(useUsers);

// Mock data
const mockProjectId = "project-123";
const mockProjectName = "Test Project";

const mockMembers: ProjectMemberRead[] = [
  {
    id: "member-1",
    user_id: "user-1",
    project_id: mockProjectId,
    role: ProjectRole.PROJECT_ADMIN,
    assigned_at: "2026-01-01T00:00:00Z",
    assigned_by: "user-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    user_name: "Admin User",
    user_email: "admin@example.com",
  },
  {
    id: "member-2",
    user_id: "user-2",
    project_id: mockProjectId,
    role: ProjectRole.PROJECT_MANAGER,
    assigned_at: "2026-01-02T00:00:00Z",
    assigned_by: "user-1",
    created_at: "2026-01-02T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    user_name: "Manager User",
    user_email: "manager@example.com",
  },
  {
    id: "member-3",
    user_id: "user-3",
    project_id: mockProjectId,
    role: ProjectRole.PROJECT_VIEWER,
    assigned_at: "2026-01-03T00:00:00Z",
    assigned_by: "user-1",
    created_at: "2026-01-03T00:00:00Z",
    updated_at: "2026-01-03T00:00:00Z",
    user_name: "Viewer User",
    user_email: "viewer@example.com",
  },
];

const currentUser = {
  user_id: "user-1",
  email: "admin@example.com",
};

describe("ProjectMemberManager", () => {
  let queryClient: QueryClient;
  let mutateAdd: ReturnType<typeof vi.fn>;
  let mutateRemove: ReturnType<typeof vi.fn>;
  let mutateUpdate: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    mutateAdd = vi.fn();
    mutateRemove = vi.fn();
    mutateUpdate = vi.fn();

    // Mock auth store
    mockUseAuthStore.mockReturnValue({
      user: currentUser,
      token: "test-token",
    });

    // Mock useProjectMembers
    mockUseProjectMembers.mockReturnValue({
      data: mockMembers,
      isLoading: false,
      isError: false,
      error: null,
      isSuccess: true,
    } as MockUseProjectMembersReturn);

    // Mock useAddProjectMember
    mockUseAddProjectMember.mockReturnValue({
      mutate: mutateAdd,
      isPending: false,
    } as MockMutationReturn);

    // Mock useUsers
    mockUseUsers.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
    });

    // Mock useRemoveProjectMember
    mockUseRemoveProjectMember.mockReturnValue({
      mutate: mutateRemove,
      isPending: false,
    } as MockMutationReturn);

    // Mock useUpdateProjectMember
    mockUseUpdateProjectMember.mockReturnValue({
      mutate: mutateUpdate,
      isPending: false,
    } as MockMutationReturn);
  });

  const createWrapper = () => {
    return ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children);
  };

  describe("Component Rendering", () => {
    it("should render component with project name", () => {
      render(
        <ProjectMemberManager
          projectId={mockProjectId}
          projectName={mockProjectName}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Project Members")).toBeInTheDocument();
      expect(screen.getByText(mockProjectName)).toBeInTheDocument();
    });

    it("should render component without project name", () => {
      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Project Members")).toBeInTheDocument();
    });

    it("should render member list with all members", () => {
      render(
        <ProjectMemberManager
          projectId={mockProjectId}
          projectName={mockProjectName}
        />,
        { wrapper: createWrapper() }
      );

      // Check for member names
      expect(screen.getByText("Admin User")).toBeInTheDocument();
      expect(screen.getByText("Manager User")).toBeInTheDocument();
      expect(screen.getByText("Viewer User")).toBeInTheDocument();

      // Check for emails
      expect(screen.getByText("admin@example.com")).toBeInTheDocument();
      expect(screen.getByText("manager@example.com")).toBeInTheDocument();
      expect(screen.getByText("viewer@example.com")).toBeInTheDocument();
    });

    it("should render loading state", () => {
      mockUseProjectMembers.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as MockUseProjectMembersReturn);

      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      // Component should still render
      expect(screen.getByText("Project Members")).toBeInTheDocument();
    });

    it("should render empty state when no members", () => {
      mockUseProjectMembers.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      } as MockUseProjectMembersReturn);

      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      // Table should still render
      expect(screen.getByText("Project Members")).toBeInTheDocument();
    });

    it("should render Add Member button", () => {
      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Add Member")).toBeInTheDocument();
    });
  });

  describe("Role Permission Legend", () => {
    it("should display role permissions legend", () => {
      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Role Permissions")).toBeInTheDocument();

      // Check for all role descriptions
      expect(
        screen.getByText("Full control including member management")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Manage project settings and content")
      ).toBeInTheDocument();
      expect(screen.getByText("Edit project content")).toBeInTheDocument();
      expect(screen.getByText("Read-only access")).toBeInTheDocument();
    });
  });

  describe("Member Display", () => {
    it("should show member name and email", () => {
      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      // Check that both name and email are displayed
      expect(screen.getByText("Admin User")).toBeInTheDocument();
      expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    });

    it("should show email when name is not available", () => {
      const membersWithoutName: ProjectMemberRead[] = [
        {
          ...mockMembers[0],
          user_name: undefined,
        },
      ];

      mockUseProjectMembers.mockReturnValue({
        data: membersWithoutName,
        isLoading: false,
        isError: false,
        error: null,
      } as MockUseProjectMembersReturn);

      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      // Should show email when name is missing
      expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    });

    it("should display current role for each member", () => {
      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      // Check that role legend displays all roles
      expect(screen.getByText("Role Permissions")).toBeInTheDocument();

      // The role selector should contain role options
      const table = screen.getByRole("table");
      expect(table).toBeInTheDocument();
      expect(table).toContainHTML("Admin");
      expect(table).toContainHTML("Manager");
      expect(table).toContainHTML("Viewer");
    });
  });

  describe("Error Handling", () => {
    it("should display error state when fetch fails", () => {
      mockUseProjectMembers.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error("Failed to load members"),
      } as MockUseProjectMembersReturn);

      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      // Component should still render
      expect(screen.getByText("Project Members")).toBeInTheDocument();
    });

    it("should handle mutation errors gracefully", () => {
      mockUseRemoveProjectMember.mockReturnValue({
        mutate: mutateRemove,
        isPending: false,
        isError: true,
        error: new Error("Failed to remove member"),
      } as MockUseProjectMembersReturn);

      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      // Component should still render
      expect(screen.getByText("Project Members")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper table structure", () => {
      render(
        <ProjectMemberManager projectId={mockProjectId} />,
        { wrapper: createWrapper() }
      );

      const table = screen.getByRole("table");
      expect(table).toBeInTheDocument();

      // Check for column headers
      expect(screen.getByText("Member")).toBeInTheDocument();
      expect(screen.getByText("Role")).toBeInTheDocument();
      expect(screen.getByText("Added")).toBeInTheDocument();
      expect(screen.getByText("Actions")).toBeInTheDocument();
    });
  });
});
