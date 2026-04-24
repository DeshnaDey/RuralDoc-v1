import type { NextConfig } from "next";

// Backend base URL — override with NEXT_PUBLIC_API_URL in production.
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7860";

const nextConfig: NextConfig = {
  // Proxy /api/* → backend so the frontend never makes cross-origin requests.
  // In dev: Next.js dev server forwards to the FastAPI backend.
  // In production: set NEXT_PUBLIC_API_URL to your deployed backend URL.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
