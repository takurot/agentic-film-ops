import type { NextConfig } from "next";
import { getPublicRuntimeConfig } from "./src/lib/runtimeConfig";

// Fail fast before Next.js can produce an export with an invalid runtime profile.
getPublicRuntimeConfig();

const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
