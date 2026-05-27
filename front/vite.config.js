import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3001,
    proxy: {
      '/health': 'http://127.0.0.1:8002',
      '/knowledge': 'http://127.0.0.1:8002',
      '/chat': 'http://127.0.0.1:8002',
      '/note': 'http://127.0.0.1:8002',
    }
  }
})
