import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { TLCPlate } from "../components/TLCPlate";
import { ComparisonTable } from "../components/ComparisonTable";

export const ComparisonScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerProgress = spring({ frame, fps, config: { damping: 18, stiffness: 85 }, durationInFrames: 22 });
  const leftProgress  = spring({ frame: Math.max(0, frame - 10), fps, config: { damping: 18, stiffness: 80 }, durationInFrames: 24 });
  const rightProgress = spring({ frame: Math.max(0, frame - 18), fps, config: { damping: 18, stiffness: 80 }, durationInFrames: 24 });
  const dividerProgress = spring({ frame: Math.max(0, frame - 5), fps, config: { damping: 20, stiffness: 120 }, durationInFrames: 20 });

  const showTable = frame > 140;
  const tlcOpacity = interpolate(frame, [140, 160], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tableOpacity = interpolate(frame, [150, 170], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: theme.colors.bg,
      padding: "100px 40px 60px",
      flexDirection: "column",
    }}>
      {/* Split background tint */}
      <div style={{
        position: "absolute", inset: 0,
        background: `linear-gradient(180deg, ${theme.colors.polarBg}44 0%, transparent 30%, ${theme.colors.nonPolarBg}44 100%)`,
      }} />

      {/* Header */}
      <div style={{
        position: "relative", zIndex: 1,
        opacity: headerProgress,
        transform: `translateY(${interpolate(headerProgress, [0, 1], [-24, 0])}px)`,
        textAlign: "center", marginBottom: 36,
      }}>
        <div style={{ fontFamily: theme.fonts.heading, fontSize: 52, fontWeight: 900, color: theme.colors.textPrimary, letterSpacing: "-0.015em", lineHeight: 1.1 }}>
          Side-by-Side{" "}
          <span style={{
            background: `linear-gradient(90deg, ${theme.colors.primary}, ${theme.colors.secondary})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
          }}>
            Comparison
          </span>
        </div>
        <div style={{ fontFamily: theme.fonts.heading, fontSize: 20, fontWeight: 500, color: theme.colors.textSecondary, marginTop: 8 }}>
          Same concept — opposite polarity
        </div>
      </div>

      {/* TLC plates side by side */}
      <div style={{
        position: "relative", zIndex: 1,
        opacity: tlcOpacity,
        display: "flex", gap: 0, justifyContent: "center", alignItems: "flex-start",
      }}>
        {/* Normal Phase */}
        <div style={{
          flex: 1, display: "flex", flexDirection: "column", alignItems: "center",
          opacity: leftProgress, transform: `translateX(${interpolate(leftProgress, [0, 1], [-20, 0])}px)`,
        }}>
          <div style={{
            fontFamily: theme.fonts.heading, fontSize: 22, fontWeight: 700,
            color: theme.colors.primary, marginBottom: 14,
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <div style={{ width: 12, height: 12, borderRadius: "50%", background: theme.colors.primary, boxShadow: `0 0 8px ${theme.colors.primary}` }} />
            Normal
          </div>
          <TLCPlate title="" delay={12} width={200} height={280} animationDuration={90}
            spots={[
              { rf: 0.75, color: theme.colors.secondary, label: "Non-polar", size: 18 },
              { rf: 0.28, color: theme.colors.primary,   label: "Polar",     size: 18 },
            ]}
          />
          <div style={{
            marginTop: 14, background: theme.colors.polarBg, border: `1px solid ${theme.colors.primary}44`,
            borderRadius: theme.radius.sm, padding: "10px 14px", textAlign: "center",
          }}>
            <div style={{ fontFamily: theme.fonts.heading, fontSize: 11, fontWeight: 700, color: theme.colors.primary, textTransform: "uppercase", letterSpacing: "0.08em" }}>Stationary</div>
            <div style={{ fontFamily: theme.fonts.heading, fontSize: 16, fontWeight: 600, color: theme.colors.textPrimary, marginTop: 2 }}>Polar (SiO₂)</div>
          </div>
        </div>

        {/* Divider */}
        <div style={{
          width: 2, alignSelf: "stretch",
          background: `linear-gradient(180deg, transparent, ${theme.colors.border}, transparent)`,
          margin: "0 16px",
          opacity: dividerProgress, transform: `scaleY(${dividerProgress})`,
        }} />

        {/* Reverse Phase */}
        <div style={{
          flex: 1, display: "flex", flexDirection: "column", alignItems: "center",
          opacity: rightProgress, transform: `translateX(${interpolate(rightProgress, [0, 1], [20, 0])}px)`,
        }}>
          <div style={{
            fontFamily: theme.fonts.heading, fontSize: 22, fontWeight: 700,
            color: theme.colors.secondary, marginBottom: 14,
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <div style={{ width: 12, height: 12, borderRadius: "50%", background: theme.colors.secondary, boxShadow: `0 0 8px ${theme.colors.secondary}` }} />
            Reverse
          </div>
          <TLCPlate title="" delay={20} width={200} height={280} animationDuration={90}
            spots={[
              { rf: 0.72, color: theme.colors.primary,   label: "Polar",     size: 18 },
              { rf: 0.24, color: theme.colors.secondary, label: "Non-polar", size: 18 },
            ]}
          />
          <div style={{
            marginTop: 14, background: theme.colors.nonPolarBg, border: `1px solid ${theme.colors.secondary}44`,
            borderRadius: theme.radius.sm, padding: "10px 14px", textAlign: "center",
          }}>
            <div style={{ fontFamily: theme.fonts.heading, fontSize: 11, fontWeight: 700, color: theme.colors.secondary, textTransform: "uppercase", letterSpacing: "0.08em" }}>Stationary</div>
            <div style={{ fontFamily: theme.fonts.heading, fontSize: 16, fontWeight: 600, color: theme.colors.textPrimary, marginTop: 2 }}>Non-polar (C18)</div>
          </div>
        </div>
      </div>

      {/* Comparison table */}
      {showTable && (
        <div style={{
          position: "absolute", inset: "180px 40px 40px", zIndex: 2,
          opacity: tableOpacity, overflowY: "hidden",
        }}>
          <ComparisonTable delay={0} />
        </div>
      )}
    </AbsoluteFill>
  );
};
