import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output is only needed for custom Docker containers, not on Vercel
  ...(process.env.DOCKER_BUILD === "1" ? { output: "standalone" } : {}),
};

export default nextConfig;
