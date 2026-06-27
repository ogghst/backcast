import { useMemo } from "react";
import { Select, Skeleton } from "antd";
import { useCustomEntityTemplates } from "../api/useCustomEntityTemplates";
import type {
  FieldDefinitions,
  TargetEntityType,
} from "../types/fieldSpec";

/**
 * TemplateSelector
 *
 * Lists CustomEntityTemplates for a given entity type and, on selection, emits
 * BOTH the template root id and its `field_definitions` — so the parent can
 * render `<CustomFieldsRenderer>` without a second fetch. The list response
 * items already carry `field_definitions` (see CustomEntityTemplateRead), so no
 * detail lookup is needed.
 *
 * The selected template root id is what the parent stores on the entity
 * (`custom_entity_template_id`); `field_definitions` is derived for rendering.
 */
interface TemplateSelectorProps {
  /** Entity type the template must target. */
  targetType: TargetEntityType;
  /** Currently selected template root id (controlled). */
  value?: string | null;
  /** Fired with (templateRootId, fieldDefinitions) on pick, (null, null) on clear. */
  onChange: (
    templateRootId: string | null,
    fieldDefinitions: FieldDefinitions | null,
  ) => void;
  disabled?: boolean;
  /** Optional org-unit scope for the template list query. */
  organizationalUnitId?: string | null;
}

export const TemplateSelector = ({
  targetType,
  value,
  onChange,
  disabled,
  organizationalUnitId,
}: TemplateSelectorProps) => {
  const { data: templates = [], isLoading } = useCustomEntityTemplates({
    target_entity_type: targetType,
    organizational_unit_id: organizationalUnitId ?? undefined,
  });

  const options = useMemo(
    () =>
      templates.map((t) => ({
        label: t.name,
        value: t.custom_entity_template_id,
      })),
    [templates],
  );

  // Index by root id so onChange can resolve field_definitions in O(1).
  const byRootId = useMemo(() => {
    const m = new Map<string, FieldDefinitions>();
    for (const t of templates) {
      m.set(t.custom_entity_template_id, t.field_definitions ?? {});
    }
    return m;
  }, [templates]);

  const handleChange = (next: string | null | undefined) => {
    if (!next) {
      onChange(null, null);
      return;
    }
    onChange(next, byRootId.get(next) ?? null);
  };

  if (isLoading) {
    return <Skeleton.Input active size="small" style={{ width: "100%" }} />;
  }

  return (
    <Select
      allowClear
      disabled={disabled}
      value={value ?? undefined}
      onChange={handleChange}
      placeholder="Select a template (optional)"
      options={options}
      style={{ width: "100%" }}
    />
  );
};
