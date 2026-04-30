import { useMemo } from "react";
import { theme as antTheme } from "antd";
import { useUserPreferencesStore } from "@/stores/useUserPreferencesStore";

interface WaveBackgroundProps {
  className?: string;
  style?: React.CSSProperties;
}

export const WaveBackground: React.FC<WaveBackgroundProps> = ({
  className,
  style,
}) => {
  const { token } = antTheme.useToken();
  const { themeMode } = useUserPreferencesStore();
  const isDark = themeMode === "dark";

  const palette = useMemo(() => {
    const base = isDark
      ? [
          token.colorPrimary + "18",
          token.colorPrimary + "10",
          token.colorInfo + "14",
          token.colorPrimary + "0c",
        ]
      : [
          token.colorPrimary + "14",
          token.colorPrimary + "0c",
          token.colorInfo + "10",
          token.colorPrimary + "08",
        ];

    return base.map((hex, i) => ({
      fill: hex,
      dur: `${14 + i * 3}s`,
      delay: `${-i * 3.5}s`,
    }));
  }, [token.colorPrimary, token.colorInfo, isDark]);

  const pathDefs = useMemo(
    () => [
      "M0,160 C320,220 480,80 720,160 C960,240 1120,60 1440,160 L1440,400 L0,400 Z",
      "M0,200 C240,260 480,140 720,200 C960,260 1200,120 1440,200 L1440,400 L0,400 Z",
      "M0,240 C200,300 500,180 720,240 C940,300 1200,160 1440,240 L1440,400 L0,400 Z",
      "M0,280 C280,320 460,220 720,280 C980,340 1180,200 1440,280 L1440,400 L0,400 Z",
    ],
    [],
  );

  return (
    <div
      className={className}
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: 0,
        ...style,
      }}
      aria-hidden="true"
    >
      <svg
        preserveAspectRatio="none"
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "200%",
          height: "60%",
          minWidth: "1400px",
        }}
        viewBox="0 0 1440 400"
      >
        <defs>
          {palette.map((_, i) => (
            <style key={i}>{`
              @keyframes waveShift${i} {
                0%   { transform: translateX(0); }
                100% { transform: translateX(-50%); }
              }
            `}</style>
          ))}
        </defs>

        {palette.map((wave, i) => (
          <g
            key={i}
            style={{
              animation: `waveShift${i} ${wave.dur} linear infinite`,
              animationDelay: wave.delay,
              opacity: 1 - i * 0.1,
            }}
          >
            <path d={pathDefs[i]} fill={wave.fill} />
            <path
              d={pathDefs[i]}
              fill={wave.fill}
              transform="translate(1440, 0)"
            />
          </g>
        ))}
      </svg>
    </div>
  );
};
