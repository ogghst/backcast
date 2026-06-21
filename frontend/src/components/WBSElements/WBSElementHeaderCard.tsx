import React from "react";
import { WBSElementRead } from "@/api/generated";
import { getBranchColor } from "@/utils/formatters";
import { StatusTag } from "@/components/layout";
import { EntityHeaderCard } from "@/components/common/EntityHeaderCard";
import {
  useEVMTimeSeries,
  EntityType,
  EVMTimeSeriesGranularity,
} from "@/features/evm";

interface WBSElementHeaderCardProps {
  wbsElement: WBSElementRead;
  loading?: boolean;
  actualCosts?: string | number | null;
  currency?: string;
  controlDate?: string;
  extraContent?: React.ReactNode;
}

export const WBSElementHeaderCard = ({
  wbsElement,
  loading,
  actualCosts,
  currency,
  controlDate,
  extraContent,
}: WBSElementHeaderCardProps) => {
  // Fetch WBS-level schedule window from the EVM time-series (cache-shared with
  // the page's CostHistoryChart). start_date/end_date are top-level on the
  // response, so this also supplies the time donut.
  const { data: evmTs } = useEVMTimeSeries(
    EntityType.WBS_ELEMENT,
    wbsElement.wbs_element_id,
    EVMTimeSeriesGranularity.WEEK,
    { controlDate } as Parameters<typeof useEVMTimeSeries>[3],
  );

  return (
    <EntityHeaderCard
      title={`${wbsElement.code} — ${wbsElement.name}`}
      badge={
        <StatusTag color={getBranchColor(wbsElement.branch)}>
          {wbsElement.branch || "main"}
        </StatusTag>
      }
      description={wbsElement.description ?? undefined}
      loading={loading}
      currency={currency || "EUR"}
      scheduleStart={evmTs?.start_date}
      scheduleEnd={evmTs?.end_date}
      controlDate={controlDate}
      budget={wbsElement.budget_allocation}
      revenue={wbsElement.revenue_allocation}
      actualCosts={actualCosts}
      extraContent={extraContent}
    />
  );
};
