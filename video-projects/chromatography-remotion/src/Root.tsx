import React from "react";
import { Composition } from "remotion";
import { ChromatographyVideo, TOTAL_FRAMES } from "./Video";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ChromatographyVideo"
        component={ChromatographyVideo}
        durationInFrames={TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{}}
      />
    </>
  );
};
