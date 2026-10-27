import type { NextConfig } from "next";

const apiServer = process.env.API_SERVER_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiServer}/api/:path*` },
      { source: "/health/:path*", destination: `${apiServer}/health/:path*` },
    ];
  },
};

export default nextConfig;
