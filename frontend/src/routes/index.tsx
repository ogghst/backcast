// This module is the router configuration (not a hot-reloaded React component);
// it necessarily defines lazy() components alongside the non-component `router`
// export, so the react-refresh rule doesn't apply here.
/* eslint-disable react-refresh/only-export-components */
import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";
import AppLayout from "@/layouts/AppLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Login from "@/pages/Login";

// Eager (kept for first paint / auth gating): AppLayout, ProtectedRoute, Login.
// Everything else is code-split per route via React.lazy.
const Home = lazy(() => import("@/pages/Home"));

const UserList = lazy(() =>
  import("@/pages/admin/UserList").then((m) => ({ default: m.UserList })),
);
const OrganizationalUnitManagement = lazy(() =>
  import("@/pages/admin/OrganizationalUnitManagement").then((m) => ({
    default: m.OrganizationalUnitManagement,
  })),
);
const CostElementTypeManagement = lazy(() =>
  import("@/pages/admin/CostElementTypeManagement").then((m) => ({
    default: m.CostElementTypeManagement,
  })),
);
const CostEventTypeManagement = lazy(() =>
  import("@/pages/admin/CostEventTypeManagement").then((m) => ({
    default: m.CostEventTypeManagement,
  })),
);
const AIProviderManagement = lazy(() =>
  import("@/pages/admin/AIProviderManagement").then((m) => ({
    default: m.AIProviderManagement,
  })),
);
const AIAssistantManagement = lazy(() =>
  import("@/pages/admin/AIAssistantManagement").then((m) => ({
    default: m.AIAssistantManagement,
  })),
);
const MCPServerManagement = lazy(() =>
  import("@/pages/admin/MCPServerManagement").then((m) => ({
    default: m.MCPServerManagement,
  })),
);
const RBACConfiguration = lazy(() =>
  import("@/pages/admin/RBACConfiguration").then((m) => ({
    default: m.RBACConfiguration,
  })),
);
const RoleAssignments = lazy(() =>
  import("@/pages/admin/RoleAssignments").then((m) => ({
    default: m.RoleAssignments,
  })),
);
const SystemAdminPage = lazy(() =>
  import("@/pages/admin/SystemAdminPage").then((m) => ({
    default: m.SystemAdminPage,
  })),
);

const ProjectList = lazy(() =>
  import("@/pages/projects/ProjectList").then((m) => ({ default: m.ProjectList })),
);
const ProjectLayout = lazy(() =>
  import("@/pages/projects/ProjectLayout").then((m) => ({ default: m.ProjectLayout })),
);
const ProjectOverview = lazy(() =>
  import("@/pages/projects/ProjectOverview").then((m) => ({ default: m.ProjectOverview })),
);
const ProjectStructure = lazy(() =>
  import("@/pages/projects/ProjectStructure").then((m) => ({
    default: m.ProjectStructure,
  })),
);
// Explorer route temporarily disabled
// const ProjectExplorer = lazy(() => import("@/pages/projects/ProjectExplorer"));
const ProjectChangeOrdersPage = lazy(() =>
  import("@/pages/projects/ProjectChangeOrdersPage").then((m) => ({
    default: m.ProjectChangeOrdersPage,
  })),
);
const ProjectEVMAnalysis = lazy(() =>
  import("@/pages/projects/ProjectEVMAnalysis").then((m) => ({
    default: m.ProjectEVMAnalysis,
  })),
);
const ProjectCOQAnalysis = lazy(() =>
  import("@/pages/projects/ProjectCOQAnalysis").then((m) => ({
    default: m.ProjectCOQAnalysis,
  })),
);
const ProjectSchedulePage = lazy(() =>
  import("@/pages/projects/ProjectSchedulePage").then((m) => ({
    default: m.ProjectSchedulePage,
  })),
);

const WBSElementList = lazy(() =>
  import("@/pages/wbs-elements/WBSElementList").then((m) => ({
    default: m.WBSElementList,
  })),
);
const WBSElementLayout = lazy(() =>
  import("@/pages/wbs-elements/WBSElementLayout").then((m) => ({
    default: m.WBSElementLayout,
  })),
);
const WBSElementOverview = lazy(() =>
  import("@/pages/wbs-elements/WBSElementOverview").then((m) => ({
    default: m.WBSElementOverview,
  })),
);
const WBSElementEVMAnalysis = lazy(() =>
  import("@/pages/wbs-elements/WBSElementEVMAnalysis").then((m) => ({
    default: m.WBSElementEVMAnalysis,
  })),
);
const WBSElementCostHistory = lazy(() =>
  import("@/pages/wbs-elements/WBSElementCostHistory").then((m) => ({
    default: m.WBSElementCostHistory,
  })),
);
const WBSElementChat = lazy(() =>
  import("@/pages/wbs-elements/WBSElementChat").then((m) => ({
    default: m.WBSElementChat,
  })),
);

const ChangeOrderUnifiedPage = lazy(() =>
  import("@/pages/projects/change-orders/ChangeOrderUnifiedPage").then((m) => ({
    default: m.ChangeOrderUnifiedPage,
  })),
);
const ChangeOrderImpactAnalysisPage = lazy(() =>
  import("@/pages/projects/change-orders/ChangeOrderImpactAnalysisPage").then((m) => ({
    default: m.ChangeOrderImpactAnalysisPage,
  })),
);

const CostElementLayout = lazy(() =>
  import("@/pages/cost-elements/CostElementLayout").then((m) => ({
    default: m.CostElementLayout,
  })),
);
const CostElementOverview = lazy(() =>
  import("@/pages/cost-elements/CostElementOverview").then((m) => ({
    default: m.CostElementOverview,
  })),
);
const CostElementCostRegistrations = lazy(() =>
  import("@/pages/cost-elements/CostElementCostRegistrations").then((m) => ({
    default: m.CostElementCostRegistrations,
  })),
);
const CostElementCostHistory = lazy(() =>
  import("@/pages/cost-elements/CostElementCostHistory").then((m) => ({
    default: m.CostElementCostHistory,
  })),
);
const CostElementChat = lazy(() =>
  import("@/pages/cost-elements/CostElementChat").then((m) => ({
    default: m.CostElementChat,
  })),
);
const CostElementDocuments = lazy(() =>
  import("@/pages/cost-elements/CostElementDocuments").then((m) => ({
    default: m.CostElementDocuments,
  })),
);

const ProjectCostEvents = lazy(() =>
  import("@/pages/projects/ProjectCostEvents").then((m) => ({
    default: m.ProjectCostEvents,
  })),
);
const ProjectDocuments = lazy(() =>
  import("@/pages/projects/ProjectDocuments").then((m) => ({
    default: m.ProjectDocuments,
  })),
);
const ProjectChat = lazy(() =>
  import("@/pages/projects/ProjectChat").then((m) => ({ default: m.ProjectChat })),
);
const ProjectMembers = lazy(() =>
  import("@/pages/projects/ProjectMembers").then((m) => ({
    default: m.ProjectMembers,
  })),
);
const ProjectAdminPage = lazy(() =>
  import("@/pages/projects/ProjectAdminPage").then((m) => ({ default: m.ProjectAdminPage })),
);

const Profile = lazy(() =>
  import("@/pages/Profile").then((m) => ({ default: m.Profile })),
);
const ChatInterfacePage = lazy(() =>
  import("@/pages/chat/ChatInterface").then((m) => ({ default: m.ChatInterfacePage })),
);
const AgentsHistory = lazy(() =>
  import("@/pages/AgentsHistory").then((m) => ({ default: m.AgentsHistory })),
);
const Notifications = lazy(() =>
  import("@/pages/Notifications").then((m) => ({ default: m.Notifications })),
);

const DashboardPage = lazy(() =>
  import("@/features/widgets/pages/DashboardPage").then((m) => ({
    default: m.DashboardPage,
  })),
);
const ChangeOrderConfigPage = lazy(() =>
  import("@/features/change-orders/components/ChangeOrderConfigPage").then((m) => ({
    default: m.ChangeOrderConfigPage,
  })),
);
const ChangeOrderRedirect = lazy(() =>
  import("@/features/change-orders/components/ChangeOrderRedirect").then((m) => ({
    default: m.ChangeOrderRedirect,
  })),
);

const WBSElementDocuments = lazy(() =>
  import("@/pages/wbs-elements/WBSElementDocuments").then((m) => ({
    default: m.WBSElementDocuments,
  })),
);

const WorkPackageLayout = lazy(() =>
  import("@/pages/work-packages/WorkPackageLayout").then((m) => ({
    default: m.WorkPackageLayout,
  })),
);
const WorkPackageOverview = lazy(() =>
  import("@/pages/work-packages/WorkPackageOverview").then((m) => ({
    default: m.WorkPackageOverview,
  })),
);
const WorkPackageCostRegistrations = lazy(() =>
  import("@/pages/work-packages/WorkPackageCostRegistrations").then((m) => ({
    default: m.WorkPackageCostRegistrations,
  })),
);
const WorkPackageCostHistory = lazy(() =>
  import("@/pages/work-packages/WorkPackageCostHistory").then((m) => ({
    default: m.WorkPackageCostHistory,
  })),
);
const WorkPackageEVMAnalysis = lazy(() =>
  import("@/pages/work-packages/WorkPackageEVMAnalysis").then((m) => ({
    default: m.WorkPackageEVMAnalysis,
  })),
);
const WorkPackageDocuments = lazy(() =>
  import("@/pages/work-packages/WorkPackageDocuments").then((m) => ({
    default: m.WorkPackageDocuments,
  })),
);
const WorkPackageChat = lazy(() =>
  import("@/pages/work-packages/WorkPackageChat").then((m) => ({
    default: m.WorkPackageChat,
  })),
);

const ControlAccountLayout = lazy(() =>
  import("@/pages/control-accounts/ControlAccountLayout").then((m) => ({
    default: m.ControlAccountLayout,
  })),
);
const ControlAccountOverview = lazy(() =>
  import("@/pages/control-accounts/ControlAccountOverview").then((m) => ({
    default: m.ControlAccountOverview,
  })),
);

const workPackageChildren = [
  { index: true, element: <WorkPackageOverview /> },
  { path: "cost-registrations", element: <WorkPackageCostRegistrations /> },
  { path: "cost-history", element: <WorkPackageCostHistory /> },
  { path: "evm-analysis", element: <WorkPackageEVMAnalysis /> },
  { path: "documents", element: <WorkPackageDocuments /> },
  { path: "chat", element: <WorkPackageChat /> },
];

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        path: "/",
        element: <Home />,
      },
      {
        path: "/projects",
        element: <ProjectList />,
      },
      {
        path: "/admin/projects",
        element: <ProjectList />,
      },
      {
        path: "/admin/wbs-elements",
        element: <WBSElementList />,
      },
      {
        path: "/users",
        element: <UserList />,
      },
      {
        path: "/admin/users",
        element: <UserList />,
      },
      {
        path: "/admin/organizational-units",
        element: <OrganizationalUnitManagement />,
      },
      {
        path: "/admin/cost-element-types",
        element: <CostElementTypeManagement />,
      },
      {
        path: "/admin/cost-event-types",
        element: <CostEventTypeManagement />,
      },
      {
        path: "/admin/ai-providers",
        element: <AIProviderManagement />,
      },
      {
        path: "/admin/ai-assistants",
        element: <AIAssistantManagement />,
      },
      {
        path: "/admin/mcp-servers",
        element: <MCPServerManagement />,
      },
      {
        path: "/admin/rbac",
        element: <RBACConfiguration />,
      },
      {
        path: "/admin/system",
        element: <SystemAdminPage />,
      },
      {
        path: "/admin/role-assignments",
        element: <RoleAssignments />,
      },
      {
        path: "/admin/change-order-config",
        element: <ChangeOrderConfigPage />,
      },
      {
        path: "/chat",
        element: (
          <ProtectedRoute>
            <ChatInterfacePage />
          </ProtectedRoute>
        ),
      },
      {
        path: "/profile",
        element: <Profile />,
      },
      {
        path: "/agents-history",
        element: (
          <ProtectedRoute>
            <AgentsHistory />
          </ProtectedRoute>
        ),
      },
      {
        path: "/notifications",
        element: (
          <ProtectedRoute>
            <Notifications />
          </ProtectedRoute>
        ),
      },
      {
        path: "/change-orders/:changeOrderId",
        element: <ChangeOrderRedirect />,
      },

      {
        path: "/projects/:projectId/work-packages/:id",
        element: <WorkPackageLayout />,
        children: workPackageChildren,
      },
      {
        path: "/projects/:projectId",
        element: <ProjectLayout />,
        children: [
          {
            index: true,
            element: <ProjectOverview />,
          },
          {
            path: "structure",
            element: <ProjectStructure />,
          },
          // Explorer route temporarily disabled
          // {
          //   path: "explorer",
          //   element: <ProjectExplorer />,
          // },
          {
            path: "change-orders",
            element: <ProjectChangeOrdersPage />,
          },
          {
            path: "members",
            element: <ProjectMembers />,
          },
          {
            path: "evm-analysis",
            element: <ProjectEVMAnalysis />,
          },
          {
            path: "coq-analysis",
            element: <ProjectCOQAnalysis />,
          },
          {
            path: "schedule",
            element: <ProjectSchedulePage />,
          },
          {
            path: "cost-events",
            element: <ProjectCostEvents />,
          },
          {
            path: "documents",
            element: <ProjectDocuments />,
          },
          {
            path: "chat",
            element: <ProjectChat />,
          },
          {
            path: "dashboard",
            element: <DashboardPage />,
          },
          {
            path: "admin",
            element: <ProjectAdminPage />,
          },
        ],
      },
      {
        path: "/projects/:projectId/change-orders/:changeOrderId/impact",
        element: <ChangeOrderImpactAnalysisPage />,
      },
      {
        path: "/projects/:projectId/change-orders/new",
        element: <ChangeOrderUnifiedPage />,
      },
      {
        path: "/projects/:projectId/change-orders/:changeOrderId",
        element: <ChangeOrderUnifiedPage />,
      },
      {
        path: "/projects/:projectId/wbs-elements/:wbsElementId",
        element: <WBSElementLayout />,
        children: [
          { index: true, element: <WBSElementOverview /> },
          { path: "evm-analysis", element: <WBSElementEVMAnalysis /> },
          { path: "cost-history", element: <WBSElementCostHistory /> },
          { path: "documents", element: <WBSElementDocuments /> },
          { path: "chat", element: <WBSElementChat /> },
        ],
      },
      {
        path: "/projects/:projectId/control-accounts/:controlAccountId",
        element: <ControlAccountLayout />,
        children: [
          { index: true, element: <ControlAccountOverview /> },
        ],
      },
      {
        path: "/cost-elements/:id",
        element: <CostElementLayout />,
        children: [
          { index: true, element: <CostElementOverview /> },
          { path: "cost-registrations", element: <CostElementCostRegistrations /> },
          { path: "cost-history", element: <CostElementCostHistory /> },
          { path: "documents", element: <CostElementDocuments /> },
          { path: "chat", element: <CostElementChat /> },
        ],
      },
      {
        path: "/work-packages/:id",
        element: <WorkPackageLayout />,
        children: workPackageChildren,
      },
    ],
  },
]);
