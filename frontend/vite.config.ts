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
          proxy.on('proxyRes', (proxyRes) => {
            const contentType = String(proxyRes.headers['content-type'] || '')
            if (contentType.includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache, no-transform'
              proxyRes.headers['x-accel-buffering'] = 'no'
              delete proxyRes.headers['content-length']
              delete proxyRes.headers['content-encoding']
            }
          })
        },
      },
    }
  }
})
