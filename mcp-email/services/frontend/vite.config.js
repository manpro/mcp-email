import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3623,
    host: '0.0.0.0',
    allowedHosts: ['localhost', 'server3', '.localhost', '.local'],
    proxy: {
      '/api/email': {
        target: 'http://localhost:3015',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/email/, '/api')
      },
      '/api/ai': {
        target: 'http://localhost:8085',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/ai/, '/v1')
      },
      '/api/mcp': {
        target: 'http://localhost:3625',
        changeOrigin: true
      }
    }
  }
})