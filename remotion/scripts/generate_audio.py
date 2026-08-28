"""Pure Python ambient BGM synthesizer (cross-platform, zero external dependencies).

Generates remotion/public/audio/bgm.wav for the 90-second demo promo video.
"""

import math
import os
import struct
import wave
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent.parent / "public" / "audio"


def generate_ambient_bgm(output_path: str | Path, duration_sec: float = 90.0, sample_rate: int = 44100):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)

    # Chord progression (Dm, Bb, F, C in Hz)
    chords = [
        [146.83, 220.00, 261.63, 349.23],  # Dm7
        [116.54, 174.61, 233.08, 293.66],  # Bbmaj7
        [174.61, 220.00, 261.63, 349.23],  # Fmaj7
        [130.81, 196.00, 261.63, 329.63],  # C7
    ]
    chord_len = 5.0  # seconds per chord

    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(2)  # Stereo
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            chord_idx = int((t / chord_len) % len(chords))
            current_chord = chords[chord_idx]

            # Ambient synth pad sound
            sample_left = 0.0
            sample_right = 0.0

            # Synth pad frequencies
            for note_idx, freq in enumerate(current_chord):
                amp = 0.12 / len(current_chord)
                # gentle warm detune and stereo panning
                detune_l = math.sin(2 * math.pi * (freq * 0.998) * t)
                detune_r = math.sin(2 * math.pi * (freq * 1.002) * t)
                harmonic = 0.3 * math.sin(2 * math.pi * (freq * 2.0) * t)

                # slow pulse modulation
                lfo = 0.7 + 0.3 * math.sin(2 * math.pi * 0.2 * t + note_idx)

                sample_left += (detune_l + harmonic) * amp * lfo
                sample_right += (detune_r + harmonic) * amp * lfo

            # Subtle heartbeat bass pulse (every 1 sec)
            bass_env = math.exp(-6.0 * (t % 1.0))
            bass = 0.15 * math.sin(2 * math.pi * 55.0 * t) * bass_env
            sample_left += bass
            sample_right += bass

            # Subtle high tech arpeggio pulse
            arp_notes = [440.0, 523.25, 659.25, 783.99, 880.0]
            arp_idx = int((t * 4.0) % len(arp_notes))
            arp_freq = arp_notes[arp_idx]
            arp_env = math.exp(-12.0 * ((t * 4.0) % 1.0))
            arp = 0.04 * math.sin(2 * math.pi * arp_freq * t) * arp_env
            sample_left += arp * 0.7
            sample_right += arp * 0.3

            # Fade in (first 2s) and fade out (last 3s)
            fade = 1.0
            if t < 2.0:
                fade = t / 2.0
            elif t > duration_sec - 3.0:
                fade = max(0.0, (duration_sec - t) / 3.0)

            sample_left *= fade
            sample_right *= fade

            # Clamp to 16-bit range
            int_left = int(max(-32767, min(32767, sample_left * 32767)))
            int_right = int(max(-32767, min(32767, sample_right * 32767)))

            frames.extend(struct.pack("<hh", int_left, int_right))

        wav_file.writeframes(frames)
    print(f"Generated {output_path} ({duration_sec}s)")


if __name__ == "__main__":
    generate_ambient_bgm(AUDIO_DIR / "bgm.wav", 90.0)
