/**
 * Manual mock for echarts-for-react
 *
 * Place this in src/__mocks__/echarts-for-react.tsx
 * Vitest will automatically use this when importing echarts-for-react
 */

import React from "react";
import type { CSSProperties, ReactNode } from "react";

interface MockEChartsProps {
  style?: CSSProperties;
  className?: string;
  option: unknown;
  onChartReady?: (chart: {
    resize: () => void;
    dispose: () => void;
    on: () => void;
    off: () => void;
    getDataURL: () => string;
    isDisposed: () => boolean;
    getOption: () => unknown;
    setOption: () => void;
  }) => void;
  children?: ReactNode;
  onEvents?: Record<string, unknown>;
  [key: string]: unknown;
}

const MockECharts = React.forwardRef<HTMLDivElement, MockEChartsProps>(
  ({ style, className, option, onChartReady, onEvents, ...props }, ref) => {
     
    void onEvents;
    React.useEffect(() => {
      if (onChartReady) {
        // Mock chart instance with common methods
        const mockChart = {
          resize: () => {},
          dispose: () => {},
          on: () => {},
          off: () => {},
          getDataURL: () => "data:image/png;base64,mock",
          isDisposed: () => false,
          getOption: () => option,
          setOption: () => {},
        };
        onChartReady(mockChart);
      }
    }, [onChartReady, option]);

    return (
      <div
        ref={ref}
        data-testid="echarts-mock"
        className={className}
        style={style}
        {...props}
      >
        {/* ECharts rendering is mocked in test environment */}
      </div>
    );
  }
);

MockECharts.displayName = "MockECharts";

export const ReactECharts = MockECharts;

export default MockECharts;
