import React from "react";
import { WorkPackageRead } from "@/api/generated";
import { StatusTag } from "@/components/layout";
import { EntityHeaderCard } from "@/components/common/EntityHeaderCard";

/** Status → color map matching the WorkPackageOverview page. */
const WP_STATUS_COLOR_MAP: Record<string, string> = {
  open: "blue",
  in_progress: "orange",
  closed: "green",
};

interface WorkPackageHeaderCardProps {
  workPackage: WorkPackageRead;
  loading?: boolean;
  actualCosts?: string | number | null;
  scheduleStart?: string;
  scheduleEnd?: string;
  controlDate?: string;
  currency?: string;
  extraContent?: React.ReactNode;
}

export const WorkPackageHeaderCard = ({
  workPackage,
  loading,
  actualCosts,
  scheduleStart,
  scheduleEnd,
  controlDate,
  currency,
  extraContent,
}: WorkPackageHeaderCardProps) => {
  const status = workPackage.status || "open";
  const statusColor = WP_STATUS_COLOR_MAP[status] || "default";

  return (
    <EntityHeaderCard
      title={`${workPackage.code} — ${workPackage.name}`}
      badge={<StatusTag color={statusColor}>{status}</StatusTag>}
      description={workPackage.description ?? undefined}
      loading={loading}
      currency={currency || "EUR"}
      scheduleStart={scheduleStart}
      scheduleEnd={scheduleEnd}
      controlDate={controlDate}
      budget={workPackage.budget_amount}
      /* Work Packages have no revenue → single budget ring */
      actualCosts={actualCosts}
      extraContent={extraContent}
    />
  );
};
