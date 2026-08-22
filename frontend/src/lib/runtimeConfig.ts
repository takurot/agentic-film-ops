export type PublicRuntimeConfig =
  | { mode: "RECORDED_REPLAY" }
  | { mode: "LIVE_GEMINI"; apiBase: string };

export interface PublicRuntimeEnvironment {
  mode?: string;
  apiUrl?: string;
  production?: boolean;
}

export function resolvePublicRuntimeConfig({
  mode,
  apiUrl,
  production = false,
}: PublicRuntimeEnvironment): PublicRuntimeConfig {
  if (mode === "RECORDED_REPLAY") return { mode };
  if (mode !== "LIVE_GEMINI") {
    throw new Error(
      "NEXT_PUBLIC_FILMOPS_MODE must be LIVE_GEMINI or RECORDED_REPLAY"
    );
  }
  if (!apiUrl) throw new Error("NEXT_PUBLIC_API_URL is required in LIVE_GEMINI mode");

  let url: URL;
  try {
    url = new URL(apiUrl);
  } catch {
    throw new Error("NEXT_PUBLIC_API_URL must be an absolute URL");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_API_URL must use HTTP or HTTPS");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new Error("NEXT_PUBLIC_API_URL must not contain credentials, query, or fragment");
  }
  // Normalize IPv6 brackets and fully-qualified trailing dots. URL implementations
  // may serialize IPv4-mapped IPv6 in dotted or canonical hex form, so both
  // ::ffff prefixes below are required to cover the full 127.0.0.0/8 range.
  const hostname = url.hostname.toLowerCase().replace(/^\[|\]$/g, "").replace(/\.+$/, "");
  const isLoopback =
    hostname === "localhost" ||
    hostname === "0.0.0.0" ||
    hostname.startsWith("127.") ||
    hostname === "::" ||
    hostname === "::1" ||
    hostname.startsWith("::ffff:127.") ||
    hostname.startsWith("::ffff:7f") ||
    hostname.endsWith(".localhost");
  if (production && (url.protocol !== "https:" || isLoopback)) {
    throw new Error("Production LIVE_GEMINI requires a non-loopback HTTPS API URL");
  }
  url.pathname = url.pathname.replace(/\/+$/, "");
  return { mode, apiBase: url.toString().replace(/\/$/, "") };
}

export function getPublicRuntimeConfig(): PublicRuntimeConfig {
  return resolvePublicRuntimeConfig({
    mode: process.env.NEXT_PUBLIC_FILMOPS_MODE,
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
    production: process.env.NODE_ENV === "production",
  });
}
