import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite 配置文件
// defineConfig 提供 TypeScript 类型提示，但不是必须的
export default defineConfig({
  plugins: [react()],

  // 代理配置：开发时把 /api 请求转发到后端
  // 这样前端可以直接写 fetch('/api/...') 而不用写完整的后端地址
  // 生产环境需要 Nginx 等做类似配置
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,   // 修改请求头里的 Host，避免后端拒绝请求
        secure: false,        // 允许自签名 HTTPS 证书（本地开发用）
      },
    },
  },
})
