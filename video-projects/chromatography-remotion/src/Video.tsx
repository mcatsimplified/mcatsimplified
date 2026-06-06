import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { TitleScene } from "./scenes/TitleScene";
import { NormalPhaseScene } from "./scenes/NormalPhaseScene";
import { ReversePhaseScene } from "./scenes/ReversePhaseScene";
import { ComparisonScene } from "./scenes/ComparisonScene";

// Scene timing at 30 fps
// 0:00–0:05  (0–150f)   Title card
// 0:05–0:25  (150–750f) Normal Phase
// 0:25–0:45  (750–1350f) Reverse Phase
// 0:45–1:15  (1350–2250f) Side-by-side Comparison
export const TOTAL_FRAMES = 2250;

const TITLE_START    = 0;
const TITLE_DUR      = 150;

const NORMAL_START   = 150;
const NORMAL_DUR     = 600;

const REVERSE_START  = 750;
const REVERSE_DUR    = 600;

const COMPARE_START  = 1350;
const COMPARE_DUR    = 900;

export const ChromatographyVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: "#0d0d1a" }}>
      {/* Voiceover track — update filename to match your trimmed lecture audio */}
      {/* <Audio src={staticFile("0605_trimmed.mp4")} /> */}

      <Sequence from={TITLE_START} durationInFrames={TITLE_DUR} name="Title">
        <TitleScene />
      </Sequence>

      <Sequence from={NORMAL_START} durationInFrames={NORMAL_DUR} name="Normal Phase">
        <NormalPhaseScene />
      </Sequence>

      <Sequence from={REVERSE_START} durationInFrames={REVERSE_DUR} name="Reverse Phase">
        <ReversePhaseScene />
      </Sequence>

      <Sequence from={COMPARE_START} durationInFrames={COMPARE_DUR} name="Comparison">
        <ComparisonScene />
      </Sequence>
    </AbsoluteFill>
  );
};
