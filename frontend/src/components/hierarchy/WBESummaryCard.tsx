import React from "react";
import { WBERead } from "@/api/generated";
import { WBEHeaderCard } from "@/components/wbes/WBEHeaderCard";
import { WBEInfoCard } from "@/components/wbes/WBEInfoCard";

interface WBESummaryCardProps {
  wbe: WBERead;
  loading?: boolean;
}

/**
 * WBESummaryCard - Redesigned WBE summary with card-based layout.
 *
 * Combines WBEHeaderCard and WBEInfoCard for a refined dashboard aesthetic.
 * Action buttons (Edit, History, Delete) are handled by the parent page component.
 */
export const WBESummaryCard = ({
  wbe,
  loading,
}: WBESummaryCardProps) => {
  return (
    <>
      <WBEHeaderCard
        wbe={wbe}
        loading={loading}
      />
      <WBEInfoCard wbe={wbe} loading={loading} />
    </>
  );
};
