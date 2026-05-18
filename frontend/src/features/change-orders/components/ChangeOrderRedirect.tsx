import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Spin, Result } from "antd";
import { useChangeOrder } from "../api/useChangeOrders";

/**
 * Redirect component that resolves a bare change-order URL
 * (`/change-orders/:changeOrderId`) to the project-scoped route
 * (`/projects/:projectId/change-orders/:changeOrderId`).
 *
 * Used by notification click navigation where only the CO id is known.
 */
export const ChangeOrderRedirect: React.FC = () => {
  const { changeOrderId } = useParams<{ changeOrderId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, error } = useChangeOrder(changeOrderId);

  React.useEffect(() => {
    if (data?.project_id) {
      navigate(
        `/projects/${data.project_id}/change-orders/${changeOrderId}`,
        { replace: true },
      );
    }
  }, [data, changeOrderId, navigate]);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "50vh",
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Result
        status="404"
        title="Change Order not found"
        subTitle="The change order you are looking for does not exist or has been deleted."
      />
    );
  }

  // Brief flash while the navigate effect fires
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "50vh",
      }}
    >
      <Spin size="large" />
    </div>
  );
};
