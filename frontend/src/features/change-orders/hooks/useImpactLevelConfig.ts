/**
 * useImpactLevelConfig - Dynamic impact level configuration hook.
 *
 * Fetches the workflow configuration (global or project-level) and derives
 * impact level colors, labels, authority levels, and SLA metadata.
 * Falls back to hardcoded defaults while loading so existing behavior is
 * preserved during the initial request.
 */
import { useMemo } from "react";
import {
  useGlobalConfig,
  useProjectConfig,
  type WorkflowConfigResponse,
} from "../api/useWorkflowConfig";

// ---------------------------------------------------------------------------
// Fallback defaults (matching the previous hardcoded values)
// ---------------------------------------------------------------------------

const FALLBACK_IMPACT_COLORS: Record<string, string> = {
  LOW: "#52c41a",
  MEDIUM: "#faad14",
  HIGH: "#fa8c16",
  CRITICAL: "#ff4d4f",
  Unassigned: "#8c8c8c",
};

const FALLBACK_TAG_COLORS: Record<string, string> = {
  LOW: "green",
  MEDIUM: "gold",
  HIGH: "orange",
  CRITICAL: "red",
};

const FALLBACK_BADGE_STYLES: Record<
  string,
  { color: string; label: string }
> = {
  LOW: { color: "success", label: "Low Impact" },
  MEDIUM: { color: "warning", label: "Medium Impact" },
  HIGH: { color: "error", label: "High Impact" },
  CRITICAL: { color: "purple", label: "Critical Impact" },
};

const FALLBACK_AUTHORITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

// ---------------------------------------------------------------------------
// Derived helpers
// ---------------------------------------------------------------------------

function deriveTagColors(
  config: WorkflowConfigResponse | undefined,
): Record<string, string> {
  if (!config) return FALLBACK_TAG_COLORS;
  const colors: Record<string, string> = {};
  for (const level of config.impact_levels) {
    colors[level.level_name] = FALLBACK_TAG_COLORS[level.level_name] ?? "default";
  }
  return colors;
}

function deriveHexColors(
  config: WorkflowConfigResponse | undefined,
): Record<string, string> {
  if (!config) return FALLBACK_IMPACT_COLORS;
  const colors: Record<string, string> = {};
  for (const level of config.impact_levels) {
    colors[level.level_name] =
      FALLBACK_IMPACT_COLORS[level.level_name] ?? "#1890ff";
  }
  return colors;
}

function deriveBadgeStyles(
  config: WorkflowConfigResponse | undefined,
): Record<string, { color: string; label: string }> {
  if (!config) return FALLBACK_BADGE_STYLES;
  const styles: Record<string, { color: string; label: string }> = {};
  for (const level of config.impact_levels) {
    styles[level.level_name] =
      FALLBACK_BADGE_STYLES[level.level_name] ??
      ({ color: "default", label: `${level.level_name} Impact` } as const);
  }
  return styles;
}

function deriveAuthorityLevels(
  config: WorkflowConfigResponse | undefined,
): string[] {
  if (!config) return FALLBACK_AUTHORITY_LEVELS;
  // Authority levels are derived from impact_levels ordered by level_order
  return [...config.impact_levels]
    .sort((a, b) => a.level_order - b.level_order)
    .map((l) => l.level_name);
}

function deriveSlaInfo(
  config: WorkflowConfigResponse | undefined,
): Record<string, { businessDays: number; escalationPct: number | null }> {
  if (!config) return {};
  const info: Record<string, { businessDays: number; escalationPct: number | null }> = {};
  for (const rule of config.sla_rules) {
    info[rule.impact_level_name] = {
      businessDays: rule.business_days,
      escalationPct: rule.escalation_trigger_pct,
    };
  }
  return info;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface ImpactLevelConfigResult {
  /** Hex color map for charts (keyed by level name, e.g. LOW) */
  impactColors: Record<string, string>;
  /** Ant Design Tag color map (keyed by level name) */
  impactTagColors: Record<string, string>;
  /** Badge style map (keyed by level name) */
  getImpactLevelStyle: (
    level: string | null,
  ) => { color: string; label: string };
  /** Ordered authority level names */
  authorityLevels: string[];
  /** SLA metadata keyed by impact level name */
  slaInfo: Record<string, { businessDays: number; escalationPct: number | null }>;
  /** Whether config is still loading */
  isLoading: boolean;
}

export function useImpactLevelConfig(
  projectId?: string,
): ImpactLevelConfigResult {
  // Fetch global config as baseline
  const globalQuery = useGlobalConfig();
  // If projectId is given, try fetching project override (may 404)
  const projectQuery = useProjectConfig(projectId, {
    enabled: !!projectId,
    retry: false,
  });

  // Use project config if it exists, otherwise fall back to global
  const activeConfig =
    projectId && projectQuery.data ? projectQuery.data : globalQuery.data;

  const isLoading =
    (projectId ? projectQuery.isLoading : false) || globalQuery.isLoading;

  return useMemo(() => {
    const impactColors = deriveHexColors(activeConfig);
    const impactTagColors = deriveTagColors(activeConfig);
    const badgeStyles = deriveBadgeStyles(activeConfig);
    const authorityLevels = deriveAuthorityLevels(activeConfig);
    const slaInfo = deriveSlaInfo(activeConfig);

    const getImpactLevelStyle = (level: string | null) =>
      badgeStyles[level || ""] ?? {
        color: "default",
        label: "Not Assessed",
      };

    return {
      impactColors,
      impactTagColors,
      getImpactLevelStyle,
      authorityLevels,
      slaInfo,
      isLoading,
    };
  }, [activeConfig, isLoading]);
}
