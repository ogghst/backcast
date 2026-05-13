import { theme, Typography } from "antd";

import { formatValue } from "../utils/formatters";

const { Text } = Typography;

interface EVMForecastBarProps {
  bac: number;
  eac: number | null;
  ac: number;
  etc: number | null;
  vac: number | null;
}

export const EVMForecastBar: React.FC<EVMForecastBarProps> = ({
  bac,
  eac,
  ac,
  etc,
  vac,
}) => {
  const { token } = theme.useToken();

  const safeBac = bac || 1;
  const eacRatio = eac !== null ? eac / safeBac : null;
  const acRatio = ac / safeBac;
  const etcRatio = etc !== null ? etc / safeBac : null;

  const isOverBudget = eac !== null && eac > safeBac;
  const vacColor =
    vac === null
      ? token.colorTextSecondary
      : vac >= 0
        ? token.colorSuccess
        : token.colorError;

  const bar2Total = Math.min(acRatio + (etcRatio ?? 0), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 4,
          }}
        >
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
            BAC {formatValue(bac, "currency")}
          </Text>
          <div style={{ display: "flex", gap: 12, alignItems: "baseline" }}>
            <Text style={{ fontSize: 12, fontWeight: 500 }}>
              EAC{" "}
              {eac !== null ? formatValue(eac, "currency") : "N/A"}
            </Text>
            {vac !== null && (
              <Text
                style={{ fontSize: 12, fontWeight: 600, color: vacColor }}
              >
                VAC {formatValue(vac, "currency")}
              </Text>
            )}
          </div>
        </div>
        <div
          style={{
            height: 10,
            borderRadius: token.borderRadiusSM,
            backgroundColor: token.colorFillSecondary,
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              height: "100%",
              width: "100%",
              backgroundColor: token.colorPrimary,
              opacity: 0.25,
              borderRadius: token.borderRadiusSM,
            }}
          />
          {eacRatio !== null && (
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                height: "100%",
                width: isOverBudget
                  ? `${Math.min(eacRatio * 100, 100)}%`
                  : `${eacRatio * 100}%`,
                backgroundColor: isOverBudget
                  ? token.colorWarning
                  : token.colorSuccess,
                opacity: 0.5,
                borderRadius: token.borderRadiusSM,
                transition: "width 0.3s ease",
              }}
            />
          )}
        </div>
      </div>

      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 4,
          }}
        >
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
            Spent {formatValue(ac, "currency")}
          </Text>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
            Remaining{" "}
            {etc !== null ? formatValue(etc, "currency") : "N/A"}
          </Text>
        </div>
        <div
          style={{
            height: 10,
            borderRadius: token.borderRadiusSM,
            backgroundColor: token.colorFillSecondary,
            display: "flex",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${Math.min(acRatio / bar2Total, 1) * 100}%`,
              backgroundColor: token.colorTextSecondary,
              opacity: 0.4,
              borderRadius: token.borderRadiusSM,
              transition: "width 0.3s ease",
            }}
          />
          <div
            style={{
              height: "100%",
              width: `${etcRatio !== null ? Math.min(etcRatio / bar2Total, 1) * 100 : 0}%`,
              backgroundColor: token.colorPrimary,
              opacity: 0.3,
              transition: "width 0.3s ease",
            }}
          />
        </div>
      </div>
    </div>
  );
};
