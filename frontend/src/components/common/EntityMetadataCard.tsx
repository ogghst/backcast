import type { ReactNode } from "react";
import { Descriptions, Typography } from "antd";
import { EntityInfoCard } from "@/components/common/EntityInfoCard";
import { entityInfoDescriptionsProps } from "@/components/common/entityInfoDescriptionsProps";
import { useExtendedToken } from "@/hooks/useToken";
import { formatDateTime, formatTemporalRange } from "@/utils/formatters";

/**
 * Props for {@link EntityMetadataCard}.
 */
interface EntityMetadataCardProps {
  /** Stable root ID of the entity (shown copyable). */
  entityId: string;
  /** Label for the entity's own ID row, e.g. "Work Package ID". */
  entityIdLabel: string;
  /** Parent root ID. When null/undefined the Parent row is omitted entirely (Project). */
  parentId?: string | null;
  /** Label for the parent row, e.g. "Control Account". */
  parentLabel?: string;
  /** Human-readable parent value (name or a nav link); falls back to parentId. */
  parentValue?: ReactNode;
  /** True creation timestamp (MIN(transaction_time.lower)). */
  createdAt?: string | null;
  /** Last modification timestamp (MAX(transaction_time.lower)). */
  updatedAt?: string | null;
  /** Creator display name; rendered as `createdBy || "System"`. */
  createdBy?: string | null;
  /** Backend temporal-range object; row omitted entirely when not provided. */
  validTime?: Record<string, string | boolean | null> | null;
  /** html id for the card wrapper. */
  cardId?: string;
  /** Extra content rendered in the card header (e.g. a History action button). */
  extra?: ReactNode;
}

/**
 * Standardized entity "metadata footer" — one collapsed "Details" card pinned
 * at the bottom of every core entity page.
 *
 * Renders a fixed, consistent row set in a stable order so a user can reliably
 * find an entity's ID, parent, creation date, last-update date, and creator:
 * **Own ID · Parent · Created · Last Updated · Created By · Valid Time**.
 *
 * Reuses {@link EntityInfoCard} (collapsible, default collapsed) and
 * {@link entityInfoDescriptionsProps} for consistent styling. Wrap this at the
 * bottom of a page; move entity-specific business fields into the header or an
 * upper business card.
 *
 * @example
 * ```tsx
 * <EntityMetadataCard
 *   entityId={wp.work_package_id}
 *   entityIdLabel="Work Package ID"
 *   parentId={wp.control_account_id}
 *   parentLabel="Control Account"
 *   parentValue={wp.control_account_name || "Unknown Control Account"}
 *   createdAt={wp.created_at}
 *   updatedAt={wp.updated_at}
 *   createdBy={wp.created_by_name}
 *   validTime={wp.valid_time_formatted}
 *   cardId="wp-metadata-card"
 * />
 * ```
 */
export const EntityMetadataCard = ({
  entityId,
  entityIdLabel,
  parentId,
  parentLabel,
  parentValue,
  createdAt,
  updatedAt,
  createdBy,
  validTime,
  cardId,
  extra,
}: EntityMetadataCardProps) => {
  const { token } = useExtendedToken();

  return (
    <EntityInfoCard title="Details" id={cardId ?? "entity-metadata-card"} extra={extra}>
      <Descriptions {...entityInfoDescriptionsProps(token)}>
        <Descriptions.Item label={entityIdLabel}>
          <Typography.Text code copyable style={{ fontSize: token.fontSizeXS }}>
            {entityId}
          </Typography.Text>
        </Descriptions.Item>

        {parentId !== null && parentId !== undefined && parentLabel && (
          <Descriptions.Item label={parentLabel}>
            {parentValue ?? parentId}
          </Descriptions.Item>
        )}

        <Descriptions.Item label="Created">
          {createdAt ? formatDateTime(createdAt) : "-"}
        </Descriptions.Item>

        <Descriptions.Item label="Last Updated">
          {updatedAt ? formatDateTime(updatedAt) : "-"}
        </Descriptions.Item>

        <Descriptions.Item label="Created By">
          {createdBy || "System"}
        </Descriptions.Item>

        {validTime && (
          <Descriptions.Item label="Valid Time">
            {formatTemporalRange(validTime) || "-"}
          </Descriptions.Item>
        )}
      </Descriptions>
    </EntityInfoCard>
  );
};
