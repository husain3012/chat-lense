import type { NextConfig } from "next";
const config: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
  experimental: {
    proxyTimeout: 600000,
    middlewareClientMaxBodySize: 105 * 1024 * 1024,
  },
};
export default config;
