import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

interface LowerThirdProps {
  title: string;
  subtitle?: string;
  delay?: number;
  exitFrame?: number;
}

export const LowerThird: React.FC<LowerThirdProps> = ({
  title,
  subtitle,
  delay = 0,
  exitFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enterProgress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 16, stiffness: 100 },
    durationInFrames: 20,
  });

  const exitProgress = exitFrame
    ? spring({
        frame: frame - exitFrame,
        fps,
        config: { damping: 20, stiffness: 140 },
        durationInFrames: 18,
      })
    : 0;

  const translateY = interpolate(enterProgress, [0, 1], [60, 0]) -
                     interpolate(exitProgress, [0, 1], [0, 60]);
  const opacity    = Math.max(0,
    interpolate(enterProgress, [0, 0.4, 1], [0, 1, 1]) -
    interpolate(exitProgress, [0, 0.4, 1], [0, 0, 1])
  );

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        bottom: 80,
        transform: `translateY(${translateY}px)`,
        opacity,
        display: "flex",
        alignItems: "stretch",
      }}
    >
      {/* Accent bar */}
      <div
        style={{
          width: 5,
          borderRadius: 3,
          background: `linear-gradient(180deg, ${theme.colors.primary}, ${theme.colors.accent})`,
          marginRight: 16,
        }}
      />

      {/* Text block */}
      <div
        style={{
          background: "rgba(13,13,26,0.88)",
          backdropFilter: "blur(12px)",
          border: `1px solid ${theme.colors.border}`,
          borderRadius: theme.radius.md,
          padding: "14px 24px",
          boxShadow: theme.shadow,
        }}
      >
        <div
          style={{
            fontFamily: theme.fonts.heading,
            fontSize: 30,
            fontWeight: 800,
            color: theme.colors.textPrimary,
            letterSpacing: "-0.01em",
            lineHeight: 1.1,
          }}
        >
          {title}
        </div>
        {subtitle && (
          <div
            style={{
              fontFamily: theme.fonts.heading,
              fontSize: 18,
              fontWeight: 500,
              color: theme.colors.primary,
              marginTop: 4,
              letterSpacing: "0.03em",
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
};
