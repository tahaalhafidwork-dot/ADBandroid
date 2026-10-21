import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { backendTarget } from './port-config.mjs'

export default defineConfig(() => {
  const environment = (globalThis as typeof globalThis & { process?: { env: Record<string, string | undefined> } }).process?.env || {}
  const target = backendTarget(environment)
  console.log(`Aqarati Vite proxy: ${target}`)
  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: { '/api': { target, changeOrigin: false } },
    },
  }
})
