import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Agentic FilmOps — Autonomous Production Disruption Recovery",
  description:
    "Autonomous Production Control Tower for film and television built on Gemini 2.5 and Model Context Protocol (MCP). Multi-agent replanning, human-in-the-loop governance, and verifiable cost avoidance.",
  metadataBase: new URL("https://takurot0708.web.app"),
  openGraph: {
    title: "Agentic FilmOps — Autonomous Production Disruption Recovery",
    description:
      "Autonomous Production Control Tower for film and television built on Gemini 2.5 and Model Context Protocol (MCP). Multi-agent replanning, human-in-the-loop governance, and verifiable cost avoidance.",
    url: "https://takurot0708.web.app",
    siteName: "Agentic FilmOps",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Agentic FilmOps — Autonomous Production Disruption Recovery",
    description:
      "Autonomous Production Control Tower for film and television built on Gemini 2.5 and Model Context Protocol (MCP).",
  },
  keywords: [
    "Agentic FilmOps",
    "Gemini 2.5",
    "Model Context Protocol",
    "MCP",
    "Multi-Agent AI",
    "Film Production",
    "Production Scheduling",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-zinc-950 text-zinc-100">{children}</body>
    </html>
  );
}
