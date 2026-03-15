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
import { ProjectList } from "@/pages/projects/ProjectList";
import { ProjectLayout } from "@/pages/projects/ProjectLayout";
import { ProjectOverview } from "@/pages/projects/ProjectOverview";
import { ProjectStructure } from "@/pages/projects/ProjectStructure";
import { ProjectChangeOrdersPage } from "@/pages/projects/ProjectChangeOrdersPage";
import { ProjectEVMAnalysis } from "@/pages/projects/ProjectEVMAnalysis";
import { WBEList } from "@/pages/wbes/WBEList";
import { WBEDetailPage } from "@/pages/wbes/WBEDetailPage";
import { ChangeOrderUnifiedPage } from "@/pages/projects/change-orders/ChangeOrderUnifiedPage";
import { ChangeOrderImpactAnalysisPage } from "@/pages/projects/change-orders/ChangeOrderImpactAnalysisPage";
import { CostElementDetailPage } from "@/pages/cost-elements/CostElementDetailPage";
import { Profile } from "@/pages/Profile";
import { ChatInterfacePage } from "@/pages/chat/ChatInterface";

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
            path: "change-orders",
            element: <ProjectChangeOrdersPage />,
          },
          {
            path: "evm-analysis",
            element: <ProjectEVMAnalysis />,
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
        element: <WBEDetailPage />,
      },
      {
        path: "/cost-elements/:id",
        element: <CostElementDetailPage />,
      },
    ],
  },
]);
