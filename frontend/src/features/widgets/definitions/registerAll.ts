/**
 * Barrel file that imports all widget definitions to trigger their
 * module-level registerWidget() side effects.
 *
 * Call registerAllWidgets() at application startup (e.g. in DashboardPage)
 * to ensure all widget types are available in the registry.
 */

import "./ProjectHeaderWidget";
import "./QuickStatsBarWidget";
import "./EVMSummaryWidget";
import "./BudgetStatusWidget";
import "./CostRegistrationsWidget";
import "./WBETreeWidget";
import "./VarianceChartWidget";
import "./ProgressTrackerWidget";
import "./HealthSummaryWidget";
import "./EVMEfficiencyGaugesWidget";
import "./EVMTrendChartWidget";
import "./ForecastWidget";
import "./ChangeOrderAnalyticsWidget";
import "./ChangeOrdersListWidget";
import "./MiniGanttWidget";

export function registerAllWidgets() {
  // Widgets are registered via module-level side effects on import.
}
