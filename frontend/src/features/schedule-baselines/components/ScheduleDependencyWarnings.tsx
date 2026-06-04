/**
 * Schedule Dependency Warnings
 *
 * Computes and displays date conflict warnings for dependency links.
 * Checks FS, SS, FF, SF constraint violations based on schedule dates.
 *
 * @module features/schedule-baselines/components
 */

import { useMemo } from "react";
import { Alert, Space, theme } from "antd";
import { type ScheduleDependencyRead, type ScheduleOption, formatScheduleLabel } from "../api/useScheduleDependencies";

interface ScheduleDependencyWarningsProps {
  dependencies: ScheduleDependencyRead[];
  schedules: ScheduleOption[];
}

interface DependencyWarning {
  key: string;
  message: string;
}

const ONE_DAY_MS = 24 * 60 * 60 * 1000;

/**
 * Check dependency date constraints and return warnings.
 */
function computeWarnings(
  dependencies: ScheduleDependencyRead[],
  scheduleMap: Map<string, ScheduleOption>,
): DependencyWarning[] {
  const warnings: DependencyWarning[] = [];

  for (const dep of dependencies) {
    const pred = scheduleMap.get(dep.predecessor_id);
    const succ = scheduleMap.get(dep.successor_id);

    if (!pred || !succ || !pred.start_date || !pred.end_date || !succ.start_date || !succ.end_date) {
      continue;
    }

    const predStart = new Date(pred.start_date).getTime();
    const predEnd = new Date(pred.end_date).getTime();
    const succStart = new Date(succ.start_date).getTime();
    const succEnd = new Date(succ.end_date).getTime();
    const lagMs = dep.lag_days * ONE_DAY_MS;

    const predLabel = formatScheduleLabel(pred);
    const succLabel = formatScheduleLabel(succ);

    let violated = false;
    let description = "";

    switch (dep.dependency_type) {
      case "FS":
        // Predecessor finish + lag must be <= successor start
        if (predEnd + lagMs > succStart) {
          violated = true;
          description = `Finish-Start: "${predLabel}" ends after "${succLabel}" starts`;
        }
        break;
      case "SS":
        // Predecessor start + lag must be <= successor start
        if (predStart + lagMs > succStart) {
          violated = true;
          description = `Start-Start: "${predLabel}" starts after "${succLabel}" starts`;
        }
        break;
      case "FF":
        // Predecessor end + lag must be <= successor end
        if (predEnd + lagMs > succEnd) {
          violated = true;
          description = `Finish-Finish: "${predLabel}" finishes after "${succLabel}" finishes`;
        }
        break;
      case "SF":
        // Predecessor start + lag must be <= successor end
        if (predStart + lagMs > succEnd) {
          violated = true;
          description = `Start-Finish: "${predLabel}" starts after "${succLabel}" finishes`;
        }
        break;
    }

    if (violated) {
      warnings.push({
        key: dep.schedule_dependency_id,
        message: description,
      });
    }
  }

  return warnings;
}

export const ScheduleDependencyWarnings: React.FC<ScheduleDependencyWarningsProps> = ({
  dependencies,
  schedules,
}) => {
  const { token } = theme.useToken();

  const scheduleMap = useMemo(() => {
    const map = new Map<string, ScheduleOption>();
    for (const s of schedules) {
      map.set(s.schedule_baseline_id, s);
    }
    return map;
  }, [schedules]);

  const warnings = useMemo(
    () => computeWarnings(dependencies, scheduleMap),
    [dependencies, scheduleMap],
  );

  if (warnings.length === 0) {
    return null;
  }

  return (
    <Space
      direction="vertical"
      style={{ width: "100%", marginBottom: token.marginSM }}
      size={token.marginXXS}
    >
      {warnings.map((w) => (
        <Alert
          key={w.key}
          type="warning"
          showIcon
          message={w.message}
          style={{ padding: `${token.paddingXXS}px ${token.paddingXS}px` }}
        />
      ))}
    </Space>
  );
};
