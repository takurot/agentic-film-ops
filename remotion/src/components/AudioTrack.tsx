import React from "react";
import { Audio, staticFile } from "remotion";

interface AudioTrackProps {
  enableAudio?: boolean;
}

export const AudioTrack: React.FC<AudioTrackProps> = ({ enableAudio = true }) => {
  if (!enableAudio) return null;

  return (
    <Audio
      src={staticFile("audio/bgm.wav")}
      volume={(f) => {
        // Fade in first 30 frames, full volume 0.7, fade out last 60 frames
        if (f < 30) {
          return (f / 30) * 0.7;
        }
        if (f > 2640) {
          return Math.max(0, ((2700 - f) / 60) * 0.7);
        }
        return 0.7;
      }}
    />
  );
};
