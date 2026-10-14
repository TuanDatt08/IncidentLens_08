/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Keep verification caches separate from an already running development server.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  async rewrites() {
    const backend = (process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
    return [
      { source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` },
      { source: "/api/v2/:path*", destination: `${backend}/api/v2/:path*` },
    ];
  },
};

export default nextConfig;
