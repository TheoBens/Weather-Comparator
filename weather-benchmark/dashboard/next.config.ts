import type { NextConfig } from "next";

const allowed =
  process.env.ALLOWED_DEV_ORIGINS?.split(",")
    .map((s) => s.trim())
    .filter(Boolean) ?? [];

const nextConfig: NextConfig = {
  ...(allowed.length > 0 ? { allowedDevOrigins: allowed } : {}),
};

export default nextConfig;
