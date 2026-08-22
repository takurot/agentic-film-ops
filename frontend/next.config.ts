import type { NextConfig } from "next";
import { resolvePublicRuntimeConfig } from "./src/lib/runtimeConfig";

resolvePublicRuntimeConfig({
  mode: process.env.NEXT_PUBLIC_FILMOPS_MODE,
  apiUrl: process.env.NEXT_PUBLIC_API_URL,
  production: process.env.NODE_ENV === "production",
});

const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
