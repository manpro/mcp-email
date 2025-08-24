/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    BACKEND_URL: process.env.BACKEND_URL || 'http://backend:8000',
  },
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/img/**',
      },
      {
        protocol: 'http',
        hostname: 'backend',
        port: '8000', 
        pathname: '/img/**',
      }
    ],
  },
};

export default nextConfig;