"""Generate voiceover audio assets using macOS TTS and FFmpeg (Issue #86).

On macOS: synthesizes narration_1.wav .. narration_8.wav into remotion/public/audio/.
On Linux/CI: relies on the versioned audio assets already committed in public/audio/.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent.parent / "public" / "audio"

NARRATIONS = [
    {
        "id": "narration_1",
        "text": "Agentic FilmOps: Autonomous Production Disruption Recovery for Film and Television.",
        "rate": "185",
    },
    {
        "id": "narration_2",
        "text": "Day 27 of Production: A sudden severe thunderstorm alert threatens critical outdoor filming on Scene 42.",
        "rate": "180",
    },
    {
        "id": "narration_3",
        "text": "Instantly, Gemini-powered domain agents activate in parallel across Script, Weather, Location, Actor, and Budget systems.",
        "rate": "180",
    },
    {
        "id": "narration_4",
        "text": "Real-time MCP tool invocations propagate through the live Resource Dependency Graph, analyzing cascading impacts.",
        "rate": "180",
    },
    {
        "id": "narration_5",
        "text": "The Actor Agent negotiates with talent agency management, confirming cast availability for Emma Carter in under 30 seconds.",
        "rate": "180",
    },
    {
        "id": "narration_6",
        "text": "Constraint solvers evaluate trade-offs and present three explainable recovery options. Option A saves seventy-nine thousand eight hundred dollars with zero schedule delay.",
        "rate": "185",
    },
    {
        "id": "narration_7",
        "text": "With a single Human Producer approval, autonomous execution coordinates call sheets, soundstages, and logistics.",
        "rate": "180",
    },
    {
        "id": "narration_8",
        "text": "Incident resolved in minutes. Production preserved. Welcome to the future of agentic film production.",
        "rate": "180",
    },
]


def generate_narrations():
    if sys.platform != "darwin" or not shutil.which("say"):
        print("[INFO] 'say' command not available (non-macOS system). Using existing committed audio assets.")
        return

    if not shutil.which("ffmpeg"):
        print("[WARNING] 'ffmpeg' not found. Cannot convert AIFF to WAV. Using existing committed audio assets.")
        return

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    for item in NARRATIONS:
        aiff_path = Path(f"/tmp/{item['id']}.aiff")
        wav_path = AUDIO_DIR / f"{item['id']}.wav"

        cmd_say = ["say", "-v", "Samantha", "-r", item.get("rate", "180"), item["text"], "-o", str(aiff_path)]
        subprocess.run(cmd_say, check=True)

        cmd_ffmpeg = [
            "ffmpeg",
            "-y",
            "-i",
            str(aiff_path),
            "-ar",
            "44100",
            "-ac",
            "2",
            str(wav_path),
        ]
        subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if aiff_path.exists():
            aiff_path.unlink()

        print(f"Generated: {wav_path.relative_to(AUDIO_DIR.parent.parent)}")


if __name__ == "__main__":
    generate_narrations()
