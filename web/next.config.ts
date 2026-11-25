import type { NextConfig } from "next";

// The Flask app stays the source of truth for data and sessions. The browser only ever talks to this
// Next.js origin; /api and /auth are proxied to Flask so the session cookie lives on one domain.
const FLASK_URL = (process.env.FLASK_URL || "http://127.0.0.1:5002").replace(/\/$/, "");

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${FLASK_URL}/api/:path*` },
      { source: "/auth/:path*", destination: `${FLASK_URL}/auth/:path*` },
      { source: "/static/:path*", destination: `${FLASK_URL}/static/:path*` },
    ];
  },
};

export default nextConfig;
