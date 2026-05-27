import { createBrowserRouter } from "react-router-dom";
import AppLayout from "@/layouts/AppLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import { UserList } from "@/pages/admin/UserList";
import { OrganizationalUnitManagement } from "@/pages/admin/OrganizationalUnitManagement";
import { CostElementTypeManagement } from "@/pages/admin/CostElementTypeManagement";
import { CostEventTypeManagement } from "@/pages/admin/CostEventTypeManagement";
import { AIProviderManagement } from "@/pages/admin/AIProviderManagement";
import { AIAssistantManagement } from "@/pages/admin/AIAssistantManagement";
import { MCPServerManagement } from "@/pages/admin/MCPServerManagement";
import { RBACConfiguration } from "@/pages/admin/RBACConfiguration";
import { RoleAssignments } from "@/pages/admin/RoleAssignments";
import { ProjectList } from "@/pages/projects/ProjectList";
import { ProjectLayout } from "@/pages/projects/ProjectLayout";
import { ProjectOverview } from "@/pages/projects/ProjectOverview";
import { ProjectStructure } from "@/pages/projects/ProjectStructure";
// Explorer route temporarily disabled
// import { ProjectExplorer } from "@/pages/projects/ProjectExplorer";
import { ProjectChangeOrdersPage } from "@/pages/projects/ProjectChangeOrdersPage";
import { ProjectEVMAnalysis } from "@/pages/projects/ProjectEVMAnalysis";
import { ProjectCOQAnalysis } from "@/pages/projects/ProjectCOQAnalysis";
import { ProjectSchedulePage } from "@/pages/projects/ProjectSchedulePage";
import { WBSElementList } from "@/pages/wbs-elements/WBSElementList";
import { WBSElementLayout } from "@/pages/wbs-elements/WBSElementLayout";
import { WBSElementOverview } from "@/pages/wbs-elements/WBSElementOverview";
import { WBSElementEVMAnalysis } from "@/pages/wbs-elements/WBSElementEVMAnalysis";
import { WBSElementCostHistory } from "@/pages/wbs-elements/WBSElementCostHistory";
import { WBSElementChat } from "@/pages/wbs-elements/WBSElementChat";
import { ChangeOrderUnifiedPage } from "@/pages/projects/change-orders/ChangeOrderUnifiedPage";
import { ChangeOrderImpactAnalysisPage } from "@/pages/projects/change-orders/ChangeOrderImpactAnalysisPage";
import { CostElementLayout } from "@/pages/cost-elements/CostElementLayout";
import { CostElementOverview } from "@/pages/cost-elements/CostElementOverview";
import { CostElementCostRegistrations } from "@/pages/cost-elements/CostElementCostRegistrations";
import { CostElementCostHistory } from "@/pages/cost-elements/CostElementCostHistory";
import { ProjectCostEvents } from "@/pages/projects/ProjectCostEvents";
import { CostElementChat } from "@/pages/cost-elements/CostElementChat";
import { Profile } from "@/pages/Profile";
import { ChatInterfacePage } from "@/pages/chat/ChatInterface";
import { ProjectChat } from "@/pages/projects/ProjectChat";
import { ProjectMembers } from "@/pages/projects/ProjectMembers";
import { ProjectAdminPage } from "@/pages/projects/ProjectAdminPage";
import { DashboardPage } from "@/features/widgets/pages/DashboardPage";
import { ChangeOrderConfigPage } from "@/features/change-orders/components/ChangeOrderConfigPage";
import { ChangeOrderRedirect } from "@/features/change-orders/components/ChangeOrderRedirect";
import { ProjectDocuments } from "@/pages/projects/ProjectDocuments";
import { WBSElementDocuments } from "@/pages/wbs-elements/WBSElementDocuments";
import { CostElementDocuments } from "@/pages/cost-elements/CostElementDocuments";
import { WorkPackageLayout } from "@/pages/work-packages/WorkPackageLayout";
import { WorkPackageOverview } from "@/pages/work-packages/WorkPackageOverview";
import { WorkPackageCostRegistrations } from "@/pages/work-packages/WorkPackageCostRegistrations";
import { WorkPackageCostHistory } from "@/pages/work-packages/WorkPackageCostHistory";
import { WorkPackageEVMAnalysis } from "@/pages/work-packages/WorkPackageEVMAnalysis";
import { WorkPackageForecasts } from "@/pages/work-packages/WorkPackageForecasts";
import { WorkPackageScheduleBaselines } from "@/pages/work-packages/WorkPackageScheduleBaselines";
import { WorkPackageDocuments } from "@/pages/work-packages/WorkPackageDocuments";
import { WorkPackageChat } from "@/pages/work-packages/WorkPackageChat";

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
        path: "/change-orders/:changeOrderId",
        element: <ChangeOrderRedirect />,
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
        children: [
          { index: true, element: <WorkPackageOverview /> },
          { path: "cost-registrations", element: <WorkPackageCostRegistrations /> },
          { path: "cost-history", element: <WorkPackageCostHistory /> },
          { path: "evm-analysis", element: <WorkPackageEVMAnalysis /> },
          { path: "forecasts", element: <WorkPackageForecasts /> },
          { path: "schedule-baselines", element: <WorkPackageScheduleBaselines /> },
          { path: "documents", element: <WorkPackageDocuments /> },
          { path: "chat", element: <WorkPackageChat /> },
        ],
      },
    ],
  },
]);
