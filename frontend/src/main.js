/**
 * 应用入口
 * =======
 * 挂载 Vue 实例并注册路由。
 * ECharts 主题的注册放在组件按需引入处（见 src/utils/echartsTheme.js），
 * 不在这里全局引入 echarts，避免拖慢首屏。
 */
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(router)
app.mount('#app')
