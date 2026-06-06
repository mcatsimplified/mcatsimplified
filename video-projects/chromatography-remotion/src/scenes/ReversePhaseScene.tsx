import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { TLCPlate } from "../components/TLCPlate";
import { CalloutBubble } from "../components/CalloutBubble";
import { LowerThird } from "../components/LowerThird";

export const ReversePhaseScene: React.FC = () => {
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
        background: `linear-gradient(160deg, ${theme.colors.nonPolarBg} 0%, ${theme.colors.bg} 50%)`,
        padding: "48px 60px",
        flexDirection: "column",
      }}
    >
      {/* Background grid */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(${theme.colors.secondary}11 1px, transparent 1px),
                            linear-gradient(90deg, ${theme.colors.secondary}11 1px, transparent 1px)`,
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
            background: `linear-gradient(180deg, ${theme.colors.secondary}, ${theme.colors.danger})`,
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
            Reverse Phase
          </div>
          <div
            style={{
              fontFamily: theme.fonts.heading,
              fontSize: 18,
              fontWeight: 500,
              color: theme.colors.secondary,
              letterSpacing: "0.04em",
              marginTop: 2,
            }}
          >
            Non-polar stationary · Polar mobile
          </div>
        </div>

        {/* "REVERSED!" badge */}
        <div
          style={{
            marginLeft: 20,
            background: `${theme.colors.secondary}22`,
            border: `2px solid ${theme.colors.secondary}`,
            borderRadius: 100,
            padding: "6px 18px",
            fontFamily: theme.fonts.heading,
            fontSize: 14,
            fontWeight: 800,
            color: theme.colors.secondary,
            letterSpacing: "0.08em",
            opacity: headerProgress,
          }}
        >
          ↕ REVERSED
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
              value: "Non-polar (C18)",
              detail: "Long hydrocarbon chains attached to silica",
              color: theme.colors.secondary,
              bg: theme.colors.nonPolarBg,
            },
            {
              icon: "🌊",
              label: "Mobile Phase",
              value: "Polar solvent",
              detail: "Water, methanol, acetonitrile",
              color: theme.colors.primary,
              bg: theme.colors.polarBg,
            },
            {
              icon: "⬆️",
              label: "Elutes First",
              value: "Polar compounds",
              detail: "Low affinity for C18 → moves fast",
              color: theme.colors.success,
              bg: `${theme.colors.success}18`,
            },
            {
              icon: "⬇️",
              label: "Elutes Last",
              value: "Non-polar compounds",
              detail: "Hydrophobic interaction with C18 → sticks",
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

        {/* Right: TLC plate — spots inverted vs normal phase */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <TLCPlate
            title="Reverse Phase TLC"
            delay={10}
            width={220}
            height={360}
            animationDuration={100}
            spots={[
              { rf: 0.72, color: theme.colors.primary,   label: "Polar (methanol)" },
              { rf: 0.24, color: theme.colors.secondary, label: "Non-polar (hexane)" },
            ]}
          />
        </div>
      </div>

      {/* Memory rule */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          marginTop: 20,
          opacity: ruleProgress,
          transform: `translateY(${interpolate(ruleProgress, [0, 1], [16, 0])}px)`,
          background: `linear-gradient(90deg, ${theme.colors.secondary}22, ${theme.colors.danger}18)`,
          border: `1px solid ${theme.colors.secondary}55`,
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
          <span style={{ color: theme.colors.secondary }}>Memory trick: </span>
          Everything is flipped — non-polar sticks to C18 → low Rf (opposite of normal phase)
        </div>
      </div>

      {/* Lower third */}
      <LowerThird
        title="Reverse Phase"
        subtitle="C18 stationary · Polar eluent"
        delay={5}
      />

      {/* Callout bubbles */}
      {frame > 100 && (
        <>
          <CalloutBubble
            label="High Rf"
            value="Polar compound"
            x={860}
            y={220}
            color={theme.colors.primary}
            delay={100}
            direction="right"
          />
          <CalloutBubble
            label="Low Rf"
            value="Non-polar compound"
            x={860}
            y={370}
            color={theme.colors.secondary}
            delay={112}
            direction="right"
          />
        </>
      )}
    </AbsoluteFill>
  );
};
