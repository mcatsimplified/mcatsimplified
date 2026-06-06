import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

interface ComparisonRow {
  property: string;
  normal: string;
  reverse: string;
}

const ROWS: ComparisonRow[] = [
  { property: "Stationary Phase", normal: "Polar (silica)", reverse: "Non-polar (C18)" },
  { property: "Mobile Phase",     normal: "Non-polar (hexane)", reverse: "Polar (water/MeOH)" },
  { property: "Elutes First",     normal: "Non-polar compounds", reverse: "Polar compounds" },
  { property: "Elutes Last",      normal: "Polar compounds", reverse: "Non-polar compounds" },
  { property: "Common Use",       normal: "Lipid-soluble vitamins", reverse: "Water-soluble vitamins" },
  { property: "MCAT Tip",         normal: "Like dissolves like → polar sticks", reverse: "\"Reversed\" polarity vs normal" },
];

interface ComparisonTableProps {
  delay?: number;
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({ delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const effectiveFrame = frame - delay;

  const headerProgress = spring({
    frame: effectiveFrame,
    fps,
    config: { damping: 18, stiffness: 90 },
    durationInFrames: 20,
  });

  return (
    <div
      style={{
        width: "100%",
        fontFamily: theme.fonts.heading,
        opacity: headerProgress,
      }}
    >
      {/* Table header */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 3,
          marginBottom: 3,
        }}
      >
        {["Property", "Normal Phase", "Reverse Phase"].map((header, hi) => (
          <div
            key={hi}
            style={{
              background: hi === 0
                ? theme.colors.surface
                : hi === 1
                ? theme.colors.polarBg
                : theme.colors.nonPolarBg,
              border: `2px solid ${hi === 0 ? theme.colors.border : hi === 1 ? theme.colors.primary : theme.colors.secondary}`,
              borderRadius: theme.radius.sm,
              padding: "12px 16px",
              fontSize: 16,
              fontWeight: 700,
              color: hi === 0 ? theme.colors.textSecondary : hi === 1 ? theme.colors.primary : theme.colors.secondary,
              textAlign: "center",
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            {header}
          </div>
        ))}
      </div>

      {/* Table rows */}
      {ROWS.map((row, i) => {
        const rowProgress = spring({
          frame: Math.max(0, effectiveFrame - 10 - i * 8),
          fps,
          config: { damping: 20, stiffness: 100 },
          durationInFrames: 18,
        });

        const translateX = interpolate(rowProgress, [0, 1], [-30, 0]);

        return (
          <div
            key={i}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 3,
              marginBottom: 3,
              opacity: rowProgress,
              transform: `translateX(${translateX}px)`,
            }}
          >
            {/* Property */}
            <div
              style={{
                background: theme.colors.surface,
                border: `1px solid ${theme.colors.border}`,
                borderRadius: theme.radius.sm,
                padding: "10px 16px",
                fontSize: 14,
                fontWeight: 600,
                color: theme.colors.textSecondary,
              }}
            >
              {row.property}
            </div>

            {/* Normal phase value */}
            <div
              style={{
                background: `${theme.colors.polarBg}88`,
                border: `1px solid ${theme.colors.primary}44`,
                borderRadius: theme.radius.sm,
                padding: "10px 16px",
                fontSize: 14,
                fontWeight: 500,
                color: theme.colors.textPrimary,
                textAlign: "center",
              }}
            >
              {row.normal}
            </div>

            {/* Reverse phase value */}
            <div
              style={{
                background: `${theme.colors.nonPolarBg}88`,
                border: `1px solid ${theme.colors.secondary}44`,
                borderRadius: theme.radius.sm,
                padding: "10px 16px",
                fontSize: 14,
                fontWeight: 500,
                color: theme.colors.textPrimary,
                textAlign: "center",
              }}
            >
              {row.reverse}
            </div>
          </div>
        );
      })}
    </div>
  );
};
