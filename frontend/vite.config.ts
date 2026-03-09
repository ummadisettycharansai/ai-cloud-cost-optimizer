import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,        // bind 0.0.0.0 — fixes "refused to connect" on localhost
    port: 5173,
    strictPort: true,  // fail fast if 5173 is already in use
  },
})
