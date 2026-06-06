import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { TLCPlate } from "../components/TLCPlate";
import { LowerThird } from "../components/LowerThird";

export const NormalPhaseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerProgress = spring({ frame, fps, config: { damping: 18, stiffness: 85 }, durationInFrames: 22 });
  const ruleProgress = spring({ frame: Math.max(0, frame - 80), fps, config: { damping: 18, stiffness: 80 }, durationInFrames: 22 });

  const FACTS = [
    { icon: "🧲", label: "Stationary Phase", value: "Polar (silica)", color: theme.colors.primary, bg: theme.colors.polarBg },
    { icon: "🌊", label: "Mobile Phase",      value: "Non-polar (hexane)", color: theme.colors.secondary, bg: theme.colors.nonPolarBg },
    { icon: "⬆️", label: "Elutes First",      value: "Non-polar compounds", color: theme.colors.success, bg: `${theme.colors.success}18` },
    { icon: "⬇️", label: "Elutes Last",       value: "Polar compounds", color: theme.colors.danger, bg: `${theme.colors.danger}18` },
  ];

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(180deg, ${theme.colors.polarBg} 0%, ${theme.colors.bg} 40%)`,
      padding: "100px 50px 160px",
      flexDirection: "column",
      overflowY: "hidden",
    }}>
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `linear-gradient(${theme.colors.primary}11 1px, transparent 1px), linear-gradient(90deg, ${theme.colors.primary}11 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
      }} />

      {/* Header */}
      <div style={{
        position: "relative", zIndex: 1,
        opacity: headerProgress,
        transform: `translateY(${interpolate(headerProgress, [0, 1], [-30, 0])}px)`,
        marginBottom: 36, display: "flex", alignItems: "center", gap: 16,
      }}>
        <div style={{ width: 8, height: 56, borderRadius: 4, background: `linear-gradient(180deg, ${theme.colors.primary}, ${theme.colors.accent})` }} />
        <div>
          <div style={{ fontFamily: theme.fonts.heading, fontSize: 56, fontWeight: 900, color: theme.colors.textPrimary, letterSpacing: "-0.01em", lineHeight: 1.1 }}>
            Normal Phase
          </div>
          <div style={{ fontFamily: theme.fonts.heading, fontSize: 24, fontWeight: 500, color: theme.colors.primary, marginTop: 4 }}>
            Polar stationary · Non-polar mobile
          </div>
        </div>
      </div>

      {/* TLC plate centered */}
      <div style={{ position: "relative", zIndex: 1, display: "flex", justifyContent: "center", marginBottom: 36 }}>
        <TLCPlate
          title="Normal Phase TLC"
          delay={10} width={260} height={340} animationDuration={100}
          spots={[
            { rf: 0.75, color: theme.colors.secondary, label: "Non-polar" },
            { rf: 0.28, color: theme.colors.primary,   label: "Polar" },
          ]}
        />
      </div>

      {/* Fact cards 2-column grid */}
      <div style={{
        position: "relative", zIndex: 1,
        display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14,
        marginBottom: 24,
      }}>
        {FACTS.map((item, i) => {
          const p = spring({ frame: Math.max(0, frame - 20 - i * 8), fps, config: { damping: 20, stiffness: 100 }, durationInFrames: 20 });
          return (
            <div key={i} style={{
              background: item.bg, border: `1px solid ${item.color}44`,
              borderRadius: theme.radius.md, padding: "18px 16px",
              opacity: p, transform: `translateY(${interpolate(p, [0, 1], [16, 0])}px)`,
            }}>
              <div style={{ fontSize: 28, marginBottom: 6 }}>{item.icon}</div>
              <div style={{ fontFamily: theme.fonts.heading, fontSize: 11, fontWeight: 700, color: item.color, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>
                {item.label}
              </div>
              <div style={{ fontFamily: theme.fonts.heading, fontSize: 17, fontWeight: 700, color: theme.colors.textPrimary, lineHeight: 1.2 }}>
                {item.value}
              </div>
            </div>
          );
        })}
      </div>

      {/* Memory rule */}
      <div style={{
        position: "relative", zIndex: 1,
        opacity: ruleProgress, transform: `translateY(${interpolate(ruleProgress, [0, 1], [16, 0])}px)`,
        background: `linear-gradient(90deg, ${theme.colors.accent}22, ${theme.colors.primary}22)`,
        border: `1px solid ${theme.colors.accent}55`,
        borderRadius: theme.radius.md, padding: "18px 20px",
        display: "flex", gap: 12, alignItems: "flex-start",
      }}>
        <div style={{ fontSize: 26 }}>💡</div>
        <div style={{ fontFamily: theme.fonts.heading, fontSize: 19, fontWeight: 600, color: theme.colors.textPrimary, lineHeight: 1.4 }}>
          <span style={{ color: theme.colors.accent }}>Memory: </span>
          Polar analyte clings to polar silica → low Rf
        </div>
      </div>

      <LowerThird title="Normal Phase" subtitle="Polar silica · Non-polar eluent" delay={5} />
    </AbsoluteFill>
  );
};
