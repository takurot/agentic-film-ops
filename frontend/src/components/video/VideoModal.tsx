"use client";

import { useEffect, useRef } from "react";

export interface VideoModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoSrc?: string;
}

export function VideoModal({
  isOpen,
  onClose,
  videoSrc = "/promo-video.mp4",
}: VideoModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }

    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Promo Video Player"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4 sm:p-6 backdrop-blur-md animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="relative flex w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-zinc-700/80 bg-zinc-900 shadow-2xl">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-950/80 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h2 className="text-sm font-bold text-zinc-100 uppercase tracking-wider">
              Agentic FilmOps — Concept & Demo Showcase (90s)
            </h2>
          </div>
          <button
            type="button"
            aria-label="Close video modal"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-400 transition-colors hover:bg-zinc-700 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Video Area */}
        <div className="relative aspect-video w-full bg-black">
          <video
            ref={videoRef}
            src={videoSrc}
            controls
            autoPlay
            playsInline
            className="h-full w-full object-contain"
          >
            Your browser does not support HTML5 video playback.
          </video>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between border-t border-zinc-800 bg-zinc-950/60 px-4 py-2.5 text-xs text-zinc-400 sm:px-6">
          <span>Remotion v4 • 1080p 30fps • Voiceover & BGM</span>
          <span className="font-mono text-[11px] text-zinc-500">Press ESC or click backdrop to close</span>
        </div>
      </div>
    </div>
  );
}
