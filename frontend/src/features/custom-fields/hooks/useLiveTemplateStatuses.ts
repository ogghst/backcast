import { useMemo } from "react";
import { useCustomEntityTemplate } from "../api/useCustomEntityTemplates";
import type { FieldDefinitions, FieldStatus } from "../types/fieldSpec";

/**
 * useLiveTemplateStatuses
 *
 * Fetches the LIVE template's `field_definitions` (by root id) and returns a
 * `{ code: status }` map for the edit-form overlay. Deprecation/retirement is
 * a LIVE-template property: an admin can deprecate a field AFTER entities were
 * bound to it, so the edit form must consult the live template (not the
 * entity's captured snapshot) to decide read-only-ness — even though it
 * renders labels/values from the snapshot.
 *
 * Driven by the cached `useCustomEntityTemplate` (TanStack Query), so all
 * modals editing entities bound to the same template share one fetch. Returns
 * `undefined` while loading or when no template id is supplied (the renderer
 * then falls back to each spec's snapshot `status`, defaulting to "active").
 *
 * @param templateRootId The bound template's root id (entity field
 *   `custom_entity_template_root_id`). Pass `undefined` for template-less /
 *   first-time-bind entities — the hook then stays disabled and returns
 *   `undefined`.
 */
export const useLiveTemplateStatuses = (
  templateRootId?: string | null,
): Record<string, FieldStatus> | undefined => {
  const { data } = useCustomEntityTemplate(templateRootId ?? undefined);

  return useMemo(() => {
    if (!data) return undefined;
    const defs = (data.field_definitions ?? {}) as FieldDefinitions;
    const out: Record<string, FieldStatus> = {};
    for (const [code, spec] of Object.entries(defs)) {
      out[code] = (spec.status as FieldStatus | undefined) ?? "active";
    }
    return out;
  }, [data]);
};
