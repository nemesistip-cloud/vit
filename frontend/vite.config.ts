import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['logo.png', 'favicon.ico'],
      manifest: {
        name: 'VIT Network',
        short_name: 'VIT',
        description: 'AI-powered decentralized prediction network',
        theme_color: '#7c3aed',
        background_color: '#0c0a14',
        display: 'standalone',
        orientation: 'portrait-primary',
        start_url: '/',
        scope: '/',
        icons: [
          { src: '/logo.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
          { src: '/logo.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
        categories: ['sports', 'finance', 'productivity'],
        shortcuts: [
          { name: 'Dashboard',   short_name: 'Dash',    url: '/dashboard',   description: 'Go to Dashboard'  },
          { name: 'Predictions', short_name: 'Predict', url: '/predictions', description: 'My Predictions'   },
          { name: 'Wallet',      short_name: 'Wallet',  url: '/wallet',      description: 'VIT Wallet'       },
          { name: 'Matches',     short_name: 'Matches', url: '/matches',     description: 'Browse Matches'   },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/.*\/api\/matches/,
            handler: 'NetworkFirst',
            options: { cacheName: 'matches-cache', expiration: { maxEntries: 50, maxAgeSeconds: 300 } },
          },
          {
            urlPattern: /^https:\/\/.*\/api\/dashboard/,
            handler: 'NetworkFirst',
            options: { cacheName: 'dashboard-cache', expiration: { maxEntries: 20, maxAgeSeconds: 60 } },
          },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5000,
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      // In dev, proxy /api/* to the local FastAPI backend on port 8000
      // so the frontend works without CORS issues and without hitting production.
      // Falls back to production if the local backend isn't running.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (_err, _req, res) => {
            // Local backend not running — let the browser hit production via fetch fallback
            if (res && !res.headersSent) {
              (res as any).writeHead(503, { 'Content-Type': 'application/json' })
              ;(res as any).end(JSON.stringify({ error: 'local backend unavailable' }))
            }
          })
        },
      },
    },
  },
})
