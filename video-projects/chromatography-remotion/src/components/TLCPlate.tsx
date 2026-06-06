import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

interface Spot {
  rf: number;      // Rf value (0-1)
  color: string;
  label: string;
  size?: number;
}

interface TLCPlateProps {
  spots: Spot[];
  title: string;
  delay?: number;
  width?: number;
  height?: number;
  animationDuration?: number; // in frames
}

export const TLCPlate: React.FC<TLCPlateProps> = ({
  spots,
  title,
  delay = 0,
  width = 200,
  height = 380,
  animationDuration = 90,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const effectiveFrame = frame - delay;

  // Plate fade-in
  const plateOpacity = spring({
    frame: effectiveFrame,
    fps,
    config: { damping: 20, stiffness: 80 },
    durationInFrames: 20,
  });

  // Solvent front animation — moves from origin up toward the top
  const frontProgress = spring({
    frame: Math.max(0, effectiveFrame - 15),
    fps,
    config: { damping: 200, stiffness: 18, mass: 2.5 },
    durationInFrames: animationDuration,
  });

  // Coordinate system: 0 = top of usable area, 1 = bottom (origin)
  const PADDING     = 30;
  const usableH     = height - PADDING * 2;
  const originY     = PADDING + usableH * 0.88;   // origin line near bottom
  const frontFinalY = PADDING + usableH * 0.10;   // solvent front near top

  const frontY = interpolate(frontProgress, [0, 1], [originY, frontFinalY]);

  return (
    <div
      style={{
        opacity: plateOpacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 12,
      }}
    >
      {/* Title */}
      <div
        style={{
          fontFamily: theme.fonts.heading,
          fontSize: 18,
          fontWeight: 700,
          color: theme.colors.textPrimary,
          textAlign: "center",
          marginBottom: 4,
        }}
      >
        {title}
      </div>

      {/* Plate */}
      <div
        style={{
          position: "relative",
          width,
          height,
          background: "#f5f3ee",            // silica plate — off-white
          border: `3px solid ${theme.colors.border}`,
          borderRadius: theme.radius.sm,
          overflow: "hidden",
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        }}
      >
        {/* Solvent front line */}
        <div
          style={{
            position: "absolute",
            left: 8,
            right: 8,
            top: frontY,
            height: 2,
            background: "#3b82f6",
            opacity: frontProgress > 0.02 ? 0.7 : 0,
            borderRadius: 1,
          }}
        />

        {/* "Solvent Front" label */}
        {frontProgress > 0.05 && (
          <div
            style={{
              position: "absolute",
              right: 10,
              top: frontY - 18,
              fontFamily: theme.fonts.heading,
              fontSize: 11,
              fontWeight: 600,
              color: "#3b82f6",
              opacity: Math.min(1, (frontProgress - 0.05) * 10),
            }}
          >
            Front
          </div>
        )}

        {/* Origin line */}
        <div
          style={{
            position: "absolute",
            left: 8,
            right: 8,
            top: originY,
            height: 2,
            background: "#6b7280",
            borderRadius: 1,
          }}
        />
        <div
          style={{
            position: "absolute",
            right: 10,
            top: originY + 4,
            fontFamily: theme.fonts.heading,
            fontSize: 10,
            fontWeight: 500,
            color: "#6b7280",
          }}
        >
          Origin
        </div>

        {/* Spots */}
        {spots.map((spot, i) => {
          const spotDiameter = spot.size ?? 22;
          // Position: origin + Rf * distance_front_traveled
          const distanceTraveled = originY - frontY;
          const spotY = originY - spot.rf * distanceTraveled;

          const spotProgress = spring({
            frame: Math.max(0, effectiveFrame - 20),
            fps,
            config: { damping: 200, stiffness: 18, mass: 2.5 },
            durationInFrames: animationDuration,
          });

          const actualSpotY = interpolate(
            spotProgress,
            [0, 1],
            [originY, spotY]
          );

          const spotOpacity = spring({
            frame: effectiveFrame,
            fps,
            config: { damping: 20, stiffness: 100 },
            durationInFrames: 15,
          });

          // Rf label fades in once animation is >80% done
          const labelOpacity = interpolate(
            frontProgress,
            [0.8, 1],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          return (
            <React.Fragment key={i}>
              {/* Spot circle */}
              <div
                style={{
                  position: "absolute",
                  left: width / 2 - spotDiameter / 2 + (i - (spots.length - 1) / 2) * 30,
                  top: actualSpotY - spotDiameter / 2,
                  width: spotDiameter,
                  height: spotDiameter,
                  borderRadius: "50%",
                  background: spot.color,
                  opacity: spotOpacity,
                  boxShadow: `0 0 10px ${spot.color}88`,
                }}
              />

              {/* Rf value label */}
              <div
                style={{
                  position: "absolute",
                  left: width / 2 - spotDiameter / 2 + (i - (spots.length - 1) / 2) * 30 - 8,
                  top: actualSpotY - spotDiameter / 2 - 22,
                  fontFamily: theme.fonts.heading,
                  fontSize: 11,
                  fontWeight: 700,
                  color: spot.color,
                  opacity: labelOpacity,
                  whiteSpace: "nowrap",
                }}
              >
                Rf={spot.rf.toFixed(2)}
              </div>
            </React.Fragment>
          );
        })}
      </div>

      {/* Spot legend */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
        {spots.map((spot, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              opacity: plateOpacity,
            }}
          >
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                background: spot.color,
              }}
            />
            <span
              style={{
                fontFamily: theme.fonts.heading,
                fontSize: 14,
                fontWeight: 600,
                color: theme.colors.textSecondary,
              }}
            >
              {spot.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
