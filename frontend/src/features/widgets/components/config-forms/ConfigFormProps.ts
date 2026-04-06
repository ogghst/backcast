/**
 * Props for widget configuration form components.
 *
 * Each widget type can provide an optional config form component
 * that renders its configuration UI in the WidgetConfigDrawer.
 *
 * @typeparam TConfig - Widget-specific configuration shape
 */
export interface ConfigFormProps<TConfig = Record<string, unknown>> {
  /** Current configuration value */
  config: TConfig;
  /** Callback when configuration changes (partial updates supported) */
  onChange: (config: Partial<TConfig>) => void;
}
