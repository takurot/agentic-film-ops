#!/usr/bin/env python3
"""Generate SRT and WebVTT subtitle files for YouTube and HTML5 video playback."""

import os
from pathlib import Path

FPS = 30

SUBTITLES = [
    {
        "start_frame": 0,
        "end_frame": 150,
        "en": "Agentic FilmOps: Autonomous Production Disruption Recovery for Film & TV",
        "ja": "Agentic FilmOps: 映画・TV制作のための自律型インシデント解決プラットフォーム",
    },
    {
        "start_frame": 150,
        "end_frame": 450,
        "en": "Day 12 of Production: A sudden severe thunderstorm alert threatens critical outdoor filming on Scene 42.",
        "ja": "撮影12日目: 突然の雷雨警報により、渋谷タワー屋上でのScene 42の屋外撮影が危機に直面。",
    },
    {
        "start_frame": 450,
        "end_frame": 900,
        "en": "Instantly, Gemini-powered domain agents activate in parallel across Script, Weather, Location, Actor, and Budget systems.",
        "ja": "Gemini搭載のドメインエージェントが即座に起動し、脚本・気象・ロケ地・キャスト・予算システムを並行分析。",
    },
    {
        "start_frame": 900,
        "end_frame": 1350,
        "en": "Real-time MCP tool invocations propagate through the live Resource Dependency Graph, analyzing cascading impacts.",
        "ja": "MCPツール経由でリソース依存グラフをリアルタイム探索し、制作全体への波及影響を瞬時に特定。",
    },
    {
        "start_frame": 1350,
        "end_frame": 1650,
        "en": "The Actor Agent negotiates with talent agency management, confirming cast availability in under 30 seconds.",
        "ja": "Actor Agentがタレント事務所と自動交渉を行い、30秒以内にキャストのスケジュール調整を完了。",
    },
    {
        "start_frame": 1650,
        "end_frame": 2100,
        "en": "Constraint solvers evaluate trade-offs and present 3 explainable recovery options. Option A saves $79,800 and 3 hours.",
        "ja": "制約ソルバーが3つの代替案を算出。Option A（スタジオB振替）は$79,800の損失と3時間の遅延を回避。",
    },
    {
        "start_frame": 2100,
        "end_frame": 2400,
        "en": "With a single Human Producer approval, autonomous execution coordinates call sheets, soundstages, and logistics.",
        "ja": "プロデューサーのワンクリック承認により、スタジオ予約・機材転送・香盤表再発行を自律実行。",
    },
    {
        "start_frame": 2400,
        "end_frame": 2700,
        "en": "Incident resolved in minutes. Production preserved. Welcome to the future of agentic film production.",
        "ja": "わずか数分で危機を完全解決。エージェントによる次世代の映画制作オペレーション。",
    },
]


def frame_to_time(frame: int, is_srt: bool = True) -> str:
    total_ms = int((frame / FPS) * 1000)
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    seconds = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    sep = "," if is_srt else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{sep}{ms:03d}"


def generate_srt(lang: str) -> str:
    lines = []
    for i, sub in enumerate(SUBTITLES, 1):
        start = frame_to_time(sub["start_frame"], is_srt=True)
        end = frame_to_time(sub["end_frame"], is_srt=True)
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(sub[lang])
        lines.append("")
    return "\n".join(lines)


def generate_vtt(lang: str) -> str:
    lines = ["WEBVTT", ""]
    for i, sub in enumerate(SUBTITLES, 1):
        start = frame_to_time(sub["start_frame"], is_srt=False)
        end = frame_to_time(sub["end_frame"], is_srt=False)
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(sub[lang])
        lines.append("")
    return "\n".join(lines)


def main():
    root = Path(__file__).resolve().parent.parent
    remotion_out = root / "remotion" / "out"
    frontend_public = root / "frontend" / "public"

    remotion_out.mkdir(parents=True, exist_ok=True)
    frontend_public.mkdir(parents=True, exist_ok=True)

    targets = [
        (remotion_out / "subtitles_en.srt", generate_srt("en")),
        (remotion_out / "subtitles_ja.srt", generate_srt("ja")),
        (remotion_out / "subtitles_en.vtt", generate_vtt("en")),
        (remotion_out / "subtitles_ja.vtt", generate_vtt("ja")),
        (frontend_public / "subtitles_en.srt", generate_srt("en")),
        (frontend_public / "subtitles_ja.srt", generate_srt("ja")),
        (frontend_public / "subtitles_en.vtt", generate_vtt("en")),
        (frontend_public / "subtitles_ja.vtt", generate_vtt("ja")),
    ]

    for path, content in targets:
        path.write_text(content, encoding="utf-8")
        print(f"✅ Generated: {path}")


if __name__ == "__main__":
    main()
