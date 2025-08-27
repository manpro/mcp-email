/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: false,
  
  // Performance optimizations
  swcMinify: true,
  compress: true,
  poweredByHeader: false,
  
  // Logging configuration
  logging: {
    fetches: {
      fullUrl: false,
    },
  },
  
  // Advanced webpack configuration
  webpack: (config, { dev, isServer }) => {
    if (dev) {
      config.devtool = false; // Disable source maps in dev
    }
    
    if (!dev && !isServer) {
      // Production optimizations for client-side
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          default: false,
          vendors: false,
          // Vendor chunk for node_modules
          vendor: {
            name: 'vendor',
            test: /[\\/]node_modules[\\/]/,
            chunks: 'all',
            priority: 20,
          },
          // Common chunk for shared components
          common: {
            minChunks: 2,
            chunks: 'all',
            name: 'common',
            priority: 10,
            reuseExistingChunk: true,
          },
          // Separate chunks for large libraries
          lodash: {
            test: /[\\/]node_modules[\\/]lodash[\\/]/,
            name: 'lodash',
            chunks: 'all',
            priority: 30,
          },
          lucide: {
            test: /[\\/]node_modules[\\/]lucide-react[\\/]/,
            name: 'lucide',
            chunks: 'all', 
            priority: 30,
          }
        }
      };
    }
    
    return config;
  },
  
  // Experimental features for better performance
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['lucide-react', 'lodash'],
    
    // Enable modern JS features
    modern: true,
    
    // Better hydration performance
    optimizeServerReact: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://localhost:8000',
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