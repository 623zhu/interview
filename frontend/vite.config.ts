import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy:{
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
        rewrite: (path) => path.replace(/^\/api/, ''),
        configure(proxy) {
          proxy.on('proxyRes', (proxyRes, _req, res) => {
            const contentType = String(proxyRes.headers['content-type'] || '')
            if (contentType.includes('text/event-stream')) {
              res.setHeader('Cache-Control', 'no-cache')
              res.setHeader('X-Accel-Buffering', 'no')
            }
          })
        },
      },
    }
  }
})
