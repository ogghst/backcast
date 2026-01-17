/**
 * Progression Preview Chart Component
 *
 * Visualizes the different progression curves (Linear, Gaussian, Logarithmic)
 * for Schedule Baselines to help users understand the planned value over time.
 */

import { useMemo } from "react";
import { Space, Typography } from "antd";

const { Text } = Typography;

interface ProgressionPreviewChartProps {
  progressionType: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
  startDate: string;
  endDate: string;
  height?: number;
}

/**
 * Calculate Linear progression at a given point
 */
function linearProgress(current: number, total: number): number {
  if (total <= 0) return 0;
  const progress = current / total;
  return Math.max(0, Math.min(1, progress));
}

/**
 * Calculate Gaussian S-curve progression
 * Uses error function approximation: 0.5 * (1 + erf(3 * (t - 0.5)))
 */
function gaussianProgress(current: number, total: number): number {
  if (current <= 0) return 0;
  if (current >= total) return 1;

  const t = current / total;
  // Error function approximation
  const x = 3 * (t - 0.5);
  const erf = (x: number) => {
    const sign = x < 0 ? -1 : 1;
    x = Math.abs(x);
    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;
    const t = 1.0 / (1.0 + p * x);
    const y =
      1.0 -
      ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return sign * y;
  };

  const progress = 0.5 * (1 + erf(x));
  return Math.max(0, Math.min(1, progress));
}

/**
 * Calculate Logarithmic (front-loaded) progression
 * Uses ln(1 + t) / ln(2) normalization
 */
function logarithmicProgress(current: number, total: number): number {
  if (current <= 0) return 0;
  if (current >= total) return 1;

  const t = current / total;
  const progress = Math.log(1 + t) / Math.log(2);
  return Math.max(0, Math.min(1, progress));
}

/**
 * SVG-based progression curve chart
 */
function ProgressionCurve({
  progressionType,
  startDate,
  endDate,
  height = 200,
}: ProgressionPreviewChartProps) {
  // Generate data points for the curve
  const points = useMemo(() => {
    const start = new Date(startDate).getTime();
    const end = new Date(endDate).getTime();
    const total = end - start;

    if (total <= 0) return [];

    // Generate 100 data points for smooth curve
    const numPoints = 100;
    const dataPoints: { x: number; y: number; label: string }[] = [];

    for (let i = 0; i <= numPoints; i++) {
      const current = start + (total * i) / numPoints;
      const currentDate = new Date(current);

      let progress = 0;
      switch (progressionType) {
        case "LINEAR":
          progress = linearProgress(current - start, total);
          break;
        case "GAUSSIAN":
          progress = gaussianProgress(current - start, total);
          break;
        case "LOGARITHMIC":
          progress = logarithmicProgress(current - start, total);
          break;
      }

      dataPoints.push({
        x: i,
        y: progress,
        label: currentDate.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      });
    }

    return dataPoints;
  }, [progressionType, startDate, endDate]);

  if (points.length === 0) {
    return (
      <div
        style={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#999",
        }}
      >
        Invalid date range
      </div>
    );
  }

  // SVG dimensions
  const width = 500;
  const padding = { top: 20, right: 30, bottom: 40, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Generate SVG path
  const pathD = points
    .map((point, i) => {
      const x = padding.left + (point.x / points.length) * chartWidth;
      const y = padding.top + chartHeight - point.y * chartHeight;
      return `${i === 0 ? "M" : "L"} ${x},${y}`;
    })
    .join(" ");

  // Grid lines
  const gridLines = [0, 0.25, 0.5, 0.75, 1];
  const gridY = gridLines.map((value) =>
    padding.top + chartHeight - value * chartHeight
  );

  // Key date points (quarterly)
  const keyDatePoints = points.filter((_, i) => i % 25 === 0);

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <svg width={width} height={height} style={{ display: "block" }}>
        {/* Background */}
        <rect x={0} y={0} width={width} height={height} fill="#f5f5f5" rx={4} />

        {/* Y-axis grid lines and labels */}
        {gridY.map((y, i) => (
          <g key={i}>
            <line
              x1={padding.left}
              y1={y}
              x2={width - padding.right}
              y2={y}
              stroke="#ddd"
              strokeWidth={1}
            />
            <text
              x={padding.left - 10}
              y={y + 4}
              textAnchor="end"
              fontSize={11}
              fill="#666"
            >
              {Math.round(gridLines[i] * 100)}%
            </text>
          </g>
        ))}

        {/* Progression curve */}
        <path
          d={pathD}
          fill="none"
          stroke={progressionType === "GAUSSIAN" ? "#52c41a" : progressionType === "LOGARITHMIC" ? "#fa8c16" : "#1890ff"}
          strokeWidth={2}
        />

        {/* Area under curve */}
        <path
          d={`${pathD} L ${width - padding.right},${padding.top + chartHeight} L ${padding.left},${padding.top + chartHeight} Z`}
          fill={progressionType === "GAUSSIAN" ? "#52c41a" : progressionType === "LOGARITHMIC" ? "#fa8c16" : "#1890ff"}
          fillOpacity={0.1}
        />

        {/* Key date points */}
        {keyDatePoints.map((point, i) => {
          const x = padding.left + (point.x / points.length) * chartWidth;
          const y = padding.top + chartHeight - point.y * chartHeight;
          return (
            <g key={i}>
              <circle
                cx={x}
                cy={y}
                r={4}
                fill={progressionType === "GAUSSIAN" ? "#52c41a" : progressionType === "LOGARITHMIC" ? "#fa8c16" : "#1890ff"}
              />
              <text
                x={x}
                y={padding.top + chartHeight + 15}
                textAnchor="middle"
                fontSize={9}
                fill="#666"
              >
                {point.label}
              </text>
            </g>
          );
        })}

        {/* Y-axis label */}
        <text
          x={padding.left / 2}
          y={padding.top + chartHeight / 2}
          textAnchor="middle"
          fontSize={11}
          fill="#666"
          transform={`rotate(-90, ${padding.left / 2}, ${padding.top + chartHeight / 2})`}
        >
          Progress
        </text>
      </svg>
    </div>
  );
}

/**
 * Main component with legend and info
 */
export const ProgressionPreviewChart: React.FC<ProgressionPreviewChartProps> = (props) => {
  const getProgressionInfo = () => {
    switch (props.progressionType) {
      case "LINEAR":
        return {
          title: "Linear Progression",
          description: "Uniform progress over time. 50% complete at midpoint.",
          color: "#1890ff",
        };
      case "GAUSSIAN":
        return {
          title: "Gaussian S-Curve",
          description: "Slow start, rapid middle acceleration, tapering at end. Realistic project pattern.",
          color: "#52c41a",
        };
      case "LOGARITHMIC":
        return {
          title: "Logarithmic (Front-loaded)",
          description: "Rapid initial progress that slows over time. Good for tasks with upfront planning.",
          color: "#fa8c16",
        };
    }
  };

  const info = getProgressionInfo();

  return (
    <div>
      <Space orientation="vertical" style={{ width: "100%" }} size={16}>
        {/* Info */}
        <div>
          <Text strong style={{ color: info.color, fontSize: 12 }}>
            ● {info.title}
          </Text>
          <div style={{ marginTop: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {info.description}
            </Text>
          </div>
        </div>

        {/* Chart */}
        <ProgressionCurve {...props} />
      </Space>
    </div>
  );
};

export default ProgressionPreviewChart;
