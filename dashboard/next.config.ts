import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "export",
  // The exported UI is mounted by FastAPI at /dashboard, not site root.
  basePath: "/dashboard",
};

export default nextConfig;
