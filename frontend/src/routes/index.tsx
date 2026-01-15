import { createBrowserRouter } from "react-router-dom";
import AppLayout from "@/layouts/AppLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import { UserList } from "@/pages/admin/UserList";
import { DepartmentManagement } from "@/pages/admin/DepartmentManagement";
import { CostElementTypeManagement } from "@/pages/admin/CostElementTypeManagement";
import { ProjectList } from "@/pages/projects/ProjectList";
import { ProjectLayout } from "@/pages/projects/ProjectLayout";
import { ProjectOverview } from "@/pages/projects/ProjectOverview";
import { ProjectChangeOrdersPage } from "@/pages/projects/ProjectChangeOrdersPage";
import { ProjectDetailPage } from "@/pages/projects/ProjectDetailPage";
import { WBEList } from "@/pages/wbes/WBEList";
import { WBEDetailPage } from "@/pages/wbes/WBEDetailPage";
import { ImpactAnalysisDashboard } from "@/features/change-orders";

import { Profile } from "@/pages/Profile";

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
            path: "change-orders",
            element: <ProjectChangeOrdersPage />,
          },
        ],
      },
      {
        path: "/projects/:projectId/change-orders/:changeOrderId/impact",
        element: <ImpactAnalysisDashboard />,
      },
      {
        path: "/projects/:projectId/wbes/:wbeId",
        element: <WBEDetailPage />,
      },
    ],
  },
]);
