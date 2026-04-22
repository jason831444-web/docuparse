import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingRoot: __dirname,
  images: {
    remotePatterns: [{ protocol: "http", hostname: "localhost", port: "8000" }]
  }
};

export default nextConfig;
