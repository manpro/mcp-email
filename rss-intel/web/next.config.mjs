/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    BACKEND_URL: process.env.BACKEND_URL || 'http://backend:8000',
  },
};

export default nextConfig;