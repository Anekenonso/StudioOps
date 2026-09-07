/**
 * Two ways to reach the FastAPI backend:
 *
 *   1. Set NEXT_PUBLIC_API_BASE_URL (e.g. the Cloud Run service URL). The
 *      browser then calls FastAPI directly and no proxying happens here.
 *   2. Leave it unset (the local default). Next proxies /api and /reports to
 *      BACKEND_ORIGIN so the app works from one origin with no CORS setup.
 */
const backendOrigin = process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000'

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Emit a self-contained server bundle so the Docker runtime stage needs only
  // the .next/standalone output, not the full node_modules tree.
  output: 'standalone',
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_BASE_URL) return []
    return [
      { source: '/api/:path*', destination: `${backendOrigin}/api/:path*` },
      { source: '/reports/:path*', destination: `${backendOrigin}/reports/:path*` },
    ]
  },
}

export default nextConfig
