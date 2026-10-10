/**
 * Vite 配置
 * =========
 * 关键点：开发服务器通过 proxy 把 /api 前缀转发到 Django 后端（8001 端口），
 * 这样前端代码里只需写相对路径 /api/...，既避免了浏览器跨域（CORS）预检，
 * 也让生产部署时（同域反代）无需改一行前端代码。
 *
 * ⚠️ 后端端口是 8001 而不是 Django 默认的 8000 ——
 *    8000 已被本机另一个项目常驻占用。
 */
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      // 用 @ 指向 src，避免出现 ../../../ 这类脆弱的相对路径
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    host: '127.0.0.1',
    port: 5173,
    // 端口被占用时直接报错，而不是静默换到 5174 导致代理失效排查困难
    strictPort: true,
    open: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        // 后端路由本身就是 /api/tourism/...，因此不需要 rewrite
      },
    },
  },

  build: {
    outDir: 'dist',
    // ECharts 体积较大（约 1MB），放宽告警阈值避免构建时刷屏
    chunkSizeWarningLimit: 1500,
  },
})
