import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Vite config for NaturalDex frontend.
// envDir points at the repo root so VITE_-prefixed vars come from the shared .env.
// In dev, /api/* is proxied to the FastAPI backend so the app is same-origin.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: '..',
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
    allowedHosts: true,
  },
})