/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['localhost'],
  },
  async rewrites() {
    return [
      {
        source: '/api/workflow/:path*',
        destination: `${process.env.NEXT_PUBLIC_WORKFLOW_SERVICE_URL || 'http://localhost:8001'}/api/v1/:path*`,
      },
      {
        source: '/api/agent/:path*',
        destination: `${process.env.NEXT_PUBLIC_AGENT_SERVICE_URL || 'http://localhost:8002'}/api/v1/:path*`,
      },
      {
        source: '/api/verify/:path*',
        destination: `${process.env.NEXT_PUBLIC_VERIFICATION_SERVICE_URL || 'http://localhost:8003'}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
