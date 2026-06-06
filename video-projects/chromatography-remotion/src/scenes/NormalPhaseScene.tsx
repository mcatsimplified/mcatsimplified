import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { TLCPlate } from "../components/TLCPlate";
import { CalloutBubble } from "../components/CalloutBubble";
import { LowerThird } from "../components/LowerThird";

export const NormalPhaseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerProgress = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 85 },
    durationInFrames: 22,
  });

  const panelProgress = spring({
    frame: Math.max(0, frame - 8),
    fps,
    config: { damping: 20, stiffness: 90 },
    durationInFrames: 24,
  });

  const ruleProgress = spring({
    frame: Math.max(0, frame - 80),
    fps,
    config: { damping: 18, stiffness: 80 },
    durationInFrames: 22,
  });

  const headerY = interpolate(headerProgress, [0, 1], [-30, 0]);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${theme.colors.polarBg} 0%, ${theme.colors.bg} 50%)`,
        padding: "48px 60px",
        flexDirection: "column",
      }}
    >
      {/* Background grid */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(${theme.colors.primary}11 1px, transparent 1px),
                            linear-gradient(90deg, ${theme.colors.primary}11 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Header */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          opacity: headerProgress,
          transform: `translateY(${headerY}px)`,
          marginBottom: 32,
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <div
          style={{
            width: 8,
            height: 48,
            borderRadius: 4,
            background: `linear-gradient(180deg, ${theme.colors.primary}, ${theme.colors.accent})`,
          }}
        />
        <div>
          <div
            style={{
              fontFamily: theme.fonts.heading,
              fontSize: 42,
              fontWeight: 900,
              color: theme.colors.textPrimary,
              letterSpacing: "-0.01em",
              lineHeight: 1.1,
            }}
          >
            Normal Phase
          </div>
          <div
            style={{
              fontFamily: theme.fonts.heading,
              fontSize: 18,
              fontWeight: 500,
              color: theme.colors.primary,
              letterSpacing: "0.04em",
              marginTop: 2,
            }}
          >
            Polar stationary · Non-polar mobile
          </div>
        </div>
      </div>

      {/* Main content: left panel + TLC plate */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          gap: 48,
          flex: 1,
          alignItems: "flex-start",
        }}
      >
        {/* Left: key facts */}
        <div
          style={{
            flex: 1,
            opacity: panelProgress,
            transform: `translateX(${interpolate(panelProgress, [0, 1], [-20, 0])}px)`,
          }}
        >
          {[
            {
              icon: "🧲",
              label: "Stationary Phase",
              value: "Polar (silica)",
              detail: "Silica has –OH groups; highly polar",
              color: theme.colors.primary,
              bg: theme.colors.polarBg,
            },
            {
              icon: "🌊",
              label: "Mobile Phase",
              value: "Non-polar solvent",
              detail: "Hexane, pentane, or similar",
              color: theme.colors.secondary,
              bg: theme.colors.nonPolarBg,
            },
            {
              icon: "⬆️",
              label: "Elutes First",
              value: "Non-polar compounds",
              detail: "Low affinity for polar silica → moves fast",
              color: theme.colors.success,
              bg: `${theme.colors.success}18`,
            },
            {
              icon: "⬇️",
              label: "Elutes Last",
              value: "Polar compounds",
              detail: "Strong affinity for silica → sticks, slow",
              color: theme.colors.danger,
              bg: `${theme.colors.danger}18`,
            },
          ].map((item, i) => {
            const itemProgress = spring({
              frame: Math.max(0, frame - 15 - i * 10),
              fps,
              config: { damping: 20, stiffness: 100 },
              durationInFrames: 20,
            });
            return (
              <div
                key={i}
                style={{
                  background: item.bg,
                  border: `1px solid ${item.color}44`,
                  borderRadius: theme.radius.md,
                  padding: "16px 20px",
                  marginBottom: 12,
                  opacity: itemProgress,
                  transform: `translateX(${interpolate(itemProgress, [0, 1], [-16, 0])}px)`,
                  display: "flex",
                  gap: 14,
                  alignItems: "flex-start",
                }}
              >
                <div style={{ fontSize: 24, marginTop: 2 }}>{item.icon}</div>
                <div>
                  <div
                    style={{
                      fontFamily: theme.fonts.heading,
                      fontSize: 12,
                      fontWeight: 700,
                      color: item.color,
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
                      marginBottom: 2,
                    }}
                  >
                    {item.label}
                  </div>
                  <div
                    style={{
                      fontFamily: theme.fonts.heading,
                      fontSize: 18,
                      fontWeight: 700,
                      color: theme.colors.textPrimary,
                      lineHeight: 1.2,
                    }}
                  >
                    {item.value}
                  </div>
                  <div
                    style={{
                      fontFamily: theme.fonts.heading,
                      fontSize: 13,
                      fontWeight: 400,
                      color: theme.colors.textSecondary,
                      marginTop: 3,
                    }}
                  >
                    {item.detail}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: TLC plate */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 0,
          }}
        >
          <TLCPlate
            title="Normal Phase TLC"
            delay={10}
            width={220}
            height={360}
            animationDuration={100}
            spots={[
              { rf: 0.75, color: theme.colors.secondary, label: "Non-polar (hexane)" },
              { rf: 0.28, color: theme.colors.primary,   label: "Polar (methanol)" },
            ]}
          />
        </div>
      </div>

      {/* Memory rule — fades in late */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          marginTop: 20,
          opacity: ruleProgress,
          transform: `translateY(${interpolate(ruleProgress, [0, 1], [16, 0])}px)`,
          background: `linear-gradient(90deg, ${theme.colors.accent}22, ${theme.colors.primary}22)`,
          border: `1px solid ${theme.colors.accent}55`,
          borderRadius: theme.radius.md,
          padding: "14px 24px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div style={{ fontSize: 22 }}>💡</div>
        <div
          style={{
            fontFamily: theme.fonts.heading,
            fontSize: 16,
            fontWeight: 600,
            color: theme.colors.textPrimary,
          }}
        >
          <span style={{ color: theme.colors.accent }}>Memory trick: </span>
          "Like dissolves like" — polar analyte clings to polar silica → low Rf
        </div>
      </div>

      {/* Lower third */}
      <LowerThird
        title="Normal Phase"
        subtitle="Polar silica · Non-polar eluent"
        delay={5}
      />

      {/* Callout bubbles appear after TLC animation (~frame 100) */}
      {frame > 100 && (
        <>
          <CalloutBubble
            label="High Rf"
            value="Non-polar compound"
            x={860}
            y={220}
            color={theme.colors.secondary}
            delay={100}
            direction="right"
          />
          <CalloutBubble
            label="Low Rf"
            value="Polar compound"
            x={860}
            y={370}
            color={theme.colors.primary}
            delay={112}
            direction="right"
          />
        </>
      )}
    </AbsoluteFill>
  );
};
