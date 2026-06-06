import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { TLCPlate } from "../components/TLCPlate";
import { ComparisonTable } from "../components/ComparisonTable";

export const ComparisonScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerProgress = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 85 },
    durationInFrames: 22,
  });

  const leftProgress = spring({
    frame: Math.max(0, frame - 10),
    fps,
    config: { damping: 18, stiffness: 80 },
    durationInFrames: 24,
  });

  const rightProgress = spring({
    frame: Math.max(0, frame - 18),
    fps,
    config: { damping: 18, stiffness: 80 },
    durationInFrames: 24,
  });

  const dividerProgress = spring({
    frame: Math.max(0, frame - 5),
    fps,
    config: { damping: 20, stiffness: 120 },
    durationInFrames: 20,
  });

  const tableProgress = spring({
    frame: Math.max(0, frame - 150),
    fps,
    config: { damping: 18, stiffness: 80 },
    durationInFrames: 24,
  });

  // After 150 frames, transition from TLC view to table view
  const showTable = frame > 140;
  const tlcOpacity = interpolate(frame, [140, 160], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tableOpacity = interpolate(frame, [150, 170], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: theme.colors.bg,
        padding: "36px 48px",
        flexDirection: "column",
      }}
    >
      {/* Subtle gradient split background */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `linear-gradient(90deg, ${theme.colors.polarBg}66 0%, transparent 50%, ${theme.colors.nonPolarBg}66 100%)`,
        }}
      />

      {/* Header */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          opacity: headerProgress,
          transform: `translateY(${interpolate(headerProgress, [0, 1], [-24, 0])}px)`,
          textAlign: "center",
          marginBottom: 24,
        }}
      >
        <div
          style={{
            fontFamily: theme.fonts.heading,
            fontSize: 44,
            fontWeight: 900,
            color: theme.colors.textPrimary,
            letterSpacing: "-0.015em",
          }}
        >
          Side-by-Side{" "}
          <span
            style={{
              background: `linear-gradient(90deg, ${theme.colors.primary}, ${theme.colors.secondary})`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Comparison
          </span>
        </div>
        <div
          style={{
            fontFamily: theme.fonts.heading,
            fontSize: 16,
            fontWeight: 500,
            color: theme.colors.textSecondary,
            marginTop: 6,
            letterSpacing: "0.04em",
          }}
        >
          Everything reversed — same principle, opposite polarity
        </div>
      </div>

      {/* TLC plates side by side */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          opacity: tlcOpacity,
          display: "flex",
          gap: 0,
          justifyContent: "center",
          alignItems: "flex-start",
          flex: 1,
        }}
      >
        {/* Normal Phase column */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            opacity: leftProgress,
            transform: `translateX(${interpolate(leftProgress, [0, 1], [-24, 0])}px)`,
          }}
        >
          <div
            style={{
              fontFamily: theme.fonts.heading,
              fontSize: 20,
              fontWeight: 700,
              color: theme.colors.primary,
              marginBottom: 16,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                width: 14,
                height: 14,
                borderRadius: "50%",
                background: theme.colors.primary,
                boxShadow: `0 0 10px ${theme.colors.primary}`,
              }}
            />
            Normal Phase
          </div>

          <TLCPlate
            title=""
            delay={12}
            width={200}
            height={300}
            animationDuration={90}
            spots={[
              { rf: 0.75, color: theme.colors.secondary, label: "Non-polar", size: 20 },
              { rf: 0.28, color: theme.colors.primary,   label: "Polar",     size: 20 },
            ]}
          />

          <div
            style={{
              marginTop: 16,
              background: theme.colors.polarBg,
              border: `1px solid ${theme.colors.primary}44`,
              borderRadius: theme.radius.sm,
              padding: "10px 16px",
              maxWidth: 220,
              textAlign: "center",
            }}
          >
            <div style={{ fontFamily: theme.fonts.heading, fontSize: 12, fontWeight: 700, color: theme.colors.primary, letterSpacing: "0.08em", textTransform: "uppercase" }}>Stationary</div>
            <div style={{ fontFamily: theme.fonts.heading, fontSize: 15, fontWeight: 600, color: theme.colors.textPrimary, marginTop: 2 }}>Polar (SiO₂)</div>
          </div>
        </div>

        {/* Center divider */}
        <div
          style={{
            width: 2,
            alignSelf: "stretch",
            background: `linear-gradient(180deg, transparent, ${theme.colors.border}, transparent)`,
            margin: "0 24px",
            opacity: dividerProgress,
            transform: `scaleY(${dividerProgress})`,
          }}
        />

        {/* Reverse Phase column */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            opacity: rightProgress,
            transform: `translateX(${interpolate(rightProgress, [0, 1], [24, 0])}px)`,
          }}
        >
          <div
            style={{
              fontFamily: theme.fonts.heading,
              fontSize: 20,
              fontWeight: 700,
              color: theme.colors.secondary,
              marginBottom: 16,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                width: 14,
                height: 14,
                borderRadius: "50%",
                background: theme.colors.secondary,
                boxShadow: `0 0 10px ${theme.colors.secondary}`,
              }}
            />
            Reverse Phase
          </div>

          <TLCPlate
            title=""
            delay={20}
            width={200}
            height={300}
            animationDuration={90}
            spots={[
              { rf: 0.72, color: theme.colors.primary,   label: "Polar",     size: 20 },
              { rf: 0.24, color: theme.colors.secondary, label: "Non-polar", size: 20 },
            ]}
          />

          <div
            style={{
              marginTop: 16,
              background: theme.colors.nonPolarBg,
              border: `1px solid ${theme.colors.secondary}44`,
              borderRadius: theme.radius.sm,
              padding: "10px 16px",
              maxWidth: 220,
              textAlign: "center",
            }}
          >
            <div style={{ fontFamily: theme.fonts.heading, fontSize: 12, fontWeight: 700, color: theme.colors.secondary, letterSpacing: "0.08em", textTransform: "uppercase" }}>Stationary</div>
            <div style={{ fontFamily: theme.fonts.heading, fontSize: 15, fontWeight: 600, color: theme.colors.textPrimary, marginTop: 2 }}>Non-polar (C18)</div>
          </div>
        </div>
      </div>

      {/* Comparison table — fades in after TLC animation */}
      {showTable && (
        <div
          style={{
            position: "absolute",
            inset: "120px 48px 48px",
            zIndex: 2,
            opacity: tableOpacity,
          }}
        >
          <ComparisonTable delay={0} />
        </div>
      )}
    </AbsoluteFill>
  );
};
