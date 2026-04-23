import { createBrowserRouter } from "react-router-dom";
import AppLayout from "@/layouts/AppLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import { UserList } from "@/pages/admin/UserList";
import { DepartmentManagement } from "@/pages/admin/DepartmentManagement";
import { CostElementTypeManagement } from "@/pages/admin/CostElementTypeManagement";
import { AIProviderManagement } from "@/pages/admin/AIProviderManagement";
import { AIAssistantManagement } from "@/pages/admin/AIAssistantManagement";
import { RBACConfiguration } from "@/pages/admin/RBACConfiguration";
import { ProjectList } from "@/pages/projects/ProjectList";
import { ProjectLayout } from "@/pages/projects/ProjectLayout";
import { ProjectOverview } from "@/pages/projects/ProjectOverview";
import { ProjectStructure } from "@/pages/projects/ProjectStructure";
import { ProjectExplorer } from "@/pages/projects/ProjectExplorer";
import { ProjectChangeOrdersPage } from "@/pages/projects/ProjectChangeOrdersPage";
import { ProjectEVMAnalysis } from "@/pages/projects/ProjectEVMAnalysis";
import { ProjectSchedulePage } from "@/pages/projects/ProjectSchedulePage";
import { WBEList } from "@/pages/wbes/WBEList";
import { WBELayout } from "@/pages/wbes/WBELayout";
import { WBEOverview } from "@/pages/wbes/WBEOverview";
import { WBEEVMAnalysis } from "@/pages/wbes/WBEEVMAnalysis";
import { WBECostHistory } from "@/pages/wbes/WBECostHistory";
import { WBEChat } from "@/pages/wbes/WBEChat";
import { ChangeOrderUnifiedPage } from "@/pages/projects/change-orders/ChangeOrderUnifiedPage";
import { ChangeOrderImpactAnalysisPage } from "@/pages/projects/change-orders/ChangeOrderImpactAnalysisPage";
import { CostElementLayout } from "@/pages/cost-elements/CostElementLayout";
import { CostElementOverview } from "@/pages/cost-elements/CostElementOverview";
import { CostElementForecasts } from "@/pages/cost-elements/CostElementForecasts";
import { CostElementScheduleBaselines } from "@/pages/cost-elements/CostElementScheduleBaselines";
import { CostElementCostRegistrations } from "@/pages/cost-elements/CostElementCostRegistrations";
import { CostElementCostHistory } from "@/pages/cost-elements/CostElementCostHistory";
import { CostElementProgress } from "@/pages/cost-elements/CostElementProgress";
import { CostElementQualityEvents } from "@/pages/cost-elements/CostElementQualityEvents";
import { CostElementChat } from "@/pages/cost-elements/CostElementChat";
import { CostElementEVMAnalysis } from "@/pages/cost-elements/CostElementEVMAnalysis";
import { Profile } from "@/pages/Profile";
import { ChatInterfacePage } from "@/pages/chat/ChatInterface";
import { ProjectChat } from "@/pages/projects/ProjectChat";
import { ProjectMembers } from "@/pages/projects/ProjectMembers";
import { ProjectAdminPage } from "@/pages/projects/ProjectAdminPage";
import { DashboardPage } from "@/features/widgets/pages/DashboardPage";

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
        path: "/admin/wbes",
        element: <WBEList />,
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
        path: "/admin/departments",
        element: <DepartmentManagement />,
      },
      {
        path: "/admin/cost-element-types",
        element: <CostElementTypeManagement />,
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
        path: "/admin/rbac",
        element: <RBACConfiguration />,
      },
      {
        path: "/chat",
        element: (
          <ProtectedRoute permission="ai-chat">
            <ChatInterfacePage />
          </ProtectedRoute>
        ),
      },
      {
        path: "/profile",
        element: <Profile />,
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
          {
            path: "explorer",
            element: <ProjectExplorer />,
          },
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
            path: "schedule",
            element: <ProjectSchedulePage />,
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
        path: "/projects/:projectId/wbes/:wbeId",
        element: <WBELayout />,
        children: [
          { index: true, element: <WBEOverview /> },
          { path: "evm-analysis", element: <WBEEVMAnalysis /> },
          { path: "cost-history", element: <WBECostHistory /> },
          { path: "chat", element: <WBEChat /> },
        ],
      },
      {
        path: "/cost-elements/:id",
        element: <CostElementLayout />,
        children: [
          { index: true, element: <CostElementOverview /> },
          { path: "forecasts", element: <CostElementForecasts /> },
          { path: "schedule-baselines", element: <CostElementScheduleBaselines /> },
          { path: "cost-registrations", element: <CostElementCostRegistrations /> },
          { path: "cost-history", element: <CostElementCostHistory /> },
          { path: "evm-analysis", element: <CostElementEVMAnalysis /> },
          { path: "progress", element: <CostElementProgress /> },
          { path: "quality-events", element: <CostElementQualityEvents /> },
          { path: "chat", element: <CostElementChat /> },
        ],
      },
    ],
  },
]);
