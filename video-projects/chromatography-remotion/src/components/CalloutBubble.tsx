import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

interface CalloutBubbleProps {
  label: string;
  value: string;
  x: number;
  y: number;
  color?: string;
  delay?: number;
  direction?: "left" | "right" | "up" | "down";
}

export const CalloutBubble: React.FC<CalloutBubbleProps> = ({
  label,
  value,
  x,
  y,
  color = theme.colors.primary,
  delay = 0,
  direction = "right",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 14, stiffness: 120, mass: 0.8 },
    durationInFrames: 24,
  });

  const opacity = interpolate(progress, [0, 1], [0, 1]);
  const scale   = interpolate(progress, [0, 1], [0.75, 1]);

  const offsetMap = {
    right: { x: interpolate(progress, [0, 1], [-20, 0]), y: 0 },
    left:  { x: interpolate(progress, [0, 1], [20, 0]),  y: 0 },
    up:    { x: 0, y: interpolate(progress, [0, 1], [20, 0])  },
    down:  { x: 0, y: interpolate(progress, [0, 1], [-20, 0]) },
  };

  const offset = offsetMap[direction];

  return (
    <div
      style={{
        position: "absolute",
        left: x + offset.x,
        top: y + offset.y,
        opacity,
        transform: `scale(${scale})`,
        transformOrigin: "center left",
      }}
    >
      {/* Connector dot */}
      <div
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: color,
          position: "absolute",
          left: -5,
          top: "50%",
          transform: "translateY(-50%)",
          boxShadow: `0 0 12px ${color}`,
        }}
      />

      {/* Bubble */}
      <div
        style={{
          background: theme.colors.surface,
          border: `2px solid ${color}`,
          borderRadius: theme.radius.md,
          padding: "10px 18px",
          minWidth: 180,
          boxShadow: `0 4px 24px rgba(0,0,0,0.5), 0 0 0 1px ${color}22`,
        }}
      >
        <div
          style={{
            fontFamily: theme.fonts.heading,
            fontSize: 15,
            fontWeight: 700,
            color,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 2,
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontFamily: theme.fonts.heading,
            fontSize: 20,
            fontWeight: 600,
            color: theme.colors.textPrimary,
            lineHeight: 1.3,
          }}
        >
          {value}
        </div>
      </div>
    </div>
  );
};
