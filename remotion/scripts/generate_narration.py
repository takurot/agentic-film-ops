import os
import subprocess

NARRATIONS = [
    {
        "id": "narration_1",
        "text": "Agentic FilmOps: Autonomous Production Disruption Recovery for Film and Television.",
        "rate": "185",
    },
    {
        "id": "narration_2",
        "text": "Day 12 of Production: A sudden severe thunderstorm alert threatens critical outdoor filming on Scene 42.",
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
        "text": "The Actor Agent negotiates with talent agency management, confirming cast availability in under 30 seconds.",
        "rate": "180",
    },
    {
        "id": "narration_6",
        "text": "Constraint solvers evaluate trade-offs and present three explainable recovery options. Option A saves seventy-nine thousand eight hundred dollars and three hours.",
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
    out_dir = "/Users/takurot/src/agentic-film-ops/remotion/public/audio"
    os.makedirs(out_dir, exist_ok=True)

    for item in NARRATIONS:
        aiff_path = f"/tmp/{item['id']}.aiff"
        wav_path = os.path.join(out_dir, f"{item['id']}.wav")
        
        cmd_say = ["say", "-v", "Samantha", "-r", item.get("rate", "180"), item["text"], "-o", aiff_path]
        subprocess.run(cmd_say, check=True)
        
        cmd_ffmpeg = [
            "ffmpeg", "-y", "-i", aiff_path,
            "-ar", "44100", "-ac", "2",
            wav_path
        ]
        subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(aiff_path):
            os.remove(aiff_path)
            
        print(f"Generated: {wav_path}")

if __name__ == "__main__":
    generate_narrations()
