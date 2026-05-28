import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3001,
    proxy: {
      '/health': 'http://127.0.0.1:8005',
      '/knowledge': 'http://127.0.0.1:8005',
      '/chat': 'http://127.0.0.1:8005',
      '/note': 'http://127.0.0.1:8005',
    }
  }
})
