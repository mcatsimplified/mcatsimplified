import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoProgress = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 80 },
    durationInFrames: 25,
  });

  const titleProgress = spring({
    frame: Math.max(0, frame - 12),
    fps,
    config: { damping: 18, stiffness: 90 },
    durationInFrames: 28,
  });

  const subtitleProgress = spring({
    frame: Math.max(0, frame - 22),
    fps,
    config: { damping: 20, stiffness: 100 },
    durationInFrames: 24,
  });

  const taglineProgress = spring({
    frame: Math.max(0, frame - 34),
    fps,
    config: { damping: 20, stiffness: 100 },
    durationInFrames: 20,
  });

  const titleY = interpolate(titleProgress, [0, 1], [40, 0]);
  const subtitleY = interpolate(subtitleProgress, [0, 1], [30, 0]);
  const taglineY = interpolate(taglineProgress, [0, 1], [20, 0]);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 40%, #1a1a3e 0%, ${theme.colors.bg} 70%)`,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 0,
      }}
    >
      {/* Background grid lines */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(${theme.colors.border}22 1px, transparent 1px),
            linear-gradient(90deg, ${theme.colors.border}22 1px, transparent 1px)
          `,
          backgroundSize: "80px 80px",
          opacity: 0.5,
        }}
      />

      {/* Glow accent */}
      <div
        style={{
          position: "absolute",
          width: 600,
          height: 300,
          borderRadius: "50%",
          background: `radial-gradient(ellipse, ${theme.colors.primary}18 0%, transparent 70%)`,
          top: "20%",
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />

      {/* MCAT Simplified brand */}
      <div
        style={{
          opacity: logoProgress,
          transform: `scale(${interpolate(logoProgress, [0, 1], [0.8, 1])})`,
          fontFamily: theme.fonts.heading,
          fontSize: 20,
          fontWeight: 700,
          letterSpacing: "0.18em",
          color: theme.colors.primary,
          textTransform: "uppercase",
          marginBottom: 32,
          position: "relative",
          zIndex: 1,
        }}
      >
        MCAT Simplified
      </div>

      {/* Main title */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          textAlign: "center",
          opacity: titleProgress,
          transform: `translateY(${titleY}px)`,
        }}
      >
        <div
          style={{
            fontFamily: theme.fonts.heading,
            fontSize: 72,
            fontWeight: 900,
            lineHeight: 1.0,
            letterSpacing: "-0.02em",
            background: `linear-gradient(135deg, ${theme.colors.textPrimary} 0%, ${theme.colors.primary} 60%, ${theme.colors.accent} 100%)`,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          Chromatography
        </div>
      </div>

      {/* Subtitle */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          marginTop: 16,
          opacity: subtitleProgress,
          transform: `translateY(${subtitleY}px)`,
          display: "flex",
          alignItems: "center",
          gap: 20,
        }}
      >
        <div
          style={{
            width: 60,
            height: 3,
            borderRadius: 2,
            background: `linear-gradient(90deg, transparent, ${theme.colors.primary})`,
          }}
        />
        <div
          style={{
            fontFamily: theme.fonts.heading,
            fontSize: 28,
            fontWeight: 500,
            color: theme.colors.textSecondary,
            letterSpacing: "0.06em",
          }}
        >
          Normal Phase vs. Reverse Phase
        </div>
        <div
          style={{
            width: 60,
            height: 3,
            borderRadius: 2,
            background: `linear-gradient(90deg, ${theme.colors.secondary}, transparent)`,
          }}
        />
      </div>

      {/* Tagline pills */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          marginTop: 40,
          opacity: taglineProgress,
          transform: `translateY(${taglineY}px)`,
          display: "flex",
          gap: 16,
        }}
      >
        {[
          { label: "TLC Plates", color: theme.colors.success },
          { label: "Rf Values", color: theme.colors.primary },
          { label: "MCAT High-Yield", color: theme.colors.accent },
        ].map((pill, i) => (
          <div
            key={i}
            style={{
              background: `${pill.color}22`,
              border: `1px solid ${pill.color}66`,
              borderRadius: 100,
              padding: "8px 20px",
              fontFamily: theme.fonts.heading,
              fontSize: 15,
              fontWeight: 600,
              color: pill.color,
              letterSpacing: "0.04em",
            }}
          >
            {pill.label}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
