import React from "react";
import { Audio, Sequence, staticFile } from "remotion";

interface AudioTrackProps {
  enableAudio?: boolean;
}

const narrationWindows = [
  [0, 147],
  [150, 340],
  [450, 700],
  [900, 1120],
  [1350, 1550],
  [1650, 1910],
  [2100, 2330],
  [2400, 2580],
];

export const AudioTrack: React.FC<AudioTrackProps> = ({ enableAudio = true }) => {
  if (!enableAudio) return null;

  return (
    <>
      {/* Background Music with Auto-Ducking during Voiceover */}
      <Audio
        src={staticFile("audio/bgm.wav")}
        volume={(f) => {
          let baseVol = 0.55;

          // Check if any narration is active at frame f
          const isSpeaking = narrationWindows.some(([start, end]) => f >= start && f <= end);
          if (isSpeaking) {
            baseVol = 0.18; // Duck BGM to let spoken voice cut through clearly
          }

          // Global fade-in and fade-out
          if (f < 30) {
            return (f / 30) * baseVol;
          }
          if (f > 2640) {
            return Math.max(0, ((2700 - f) / 60) * baseVol);
          }
          return baseVol;
        }}
      />

      {/* Spoken Voice Narration Tracks per Scene */}
      <Sequence from={0} durationInFrames={150} name="Narration 1">
        <Audio src={staticFile("audio/narration_1.wav")} volume={1.0} />
      </Sequence>

      <Sequence from={150} durationInFrames={300} name="Narration 2">
        <Audio src={staticFile("audio/narration_2.wav")} volume={1.0} />
      </Sequence>

      <Sequence from={450} durationInFrames={450} name="Narration 3">
        <Audio src={staticFile("audio/narration_3.wav")} volume={1.0} />
      </Sequence>

      <Sequence from={900} durationInFrames={450} name="Narration 4">
        <Audio src={staticFile("audio/narration_4.wav")} volume={1.0} />
      </Sequence>

      <Sequence from={1350} durationInFrames={300} name="Narration 5">
        <Audio src={staticFile("audio/narration_5.wav")} volume={1.0} />
      </Sequence>

      <Sequence from={1650} durationInFrames={450} name="Narration 6">
        <Audio src={staticFile("audio/narration_6.wav")} volume={1.0} />
      </Sequence>

      <Sequence from={2100} durationInFrames={300} name="Narration 7">
        <Audio src={staticFile("audio/narration_7.wav")} volume={1.0} />
      </Sequence>

      <Sequence from={2400} durationInFrames={300} name="Narration 8">
        <Audio src={staticFile("audio/narration_8.wav")} volume={1.0} />
      </Sequence>
    </>
  );
};
