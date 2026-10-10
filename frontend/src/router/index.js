/**
 * 路由配置
 * =======
 * 本系统是单页数据大屏，目前只有一个 Dashboard 视图。
 * 采用 hash 模式（createWebHashHistory）的原因：
 *   部署到静态服务器时无需配置 history fallback 重写规则，
 *   直接刷新或带子路径访问都不会 404，答辩演示更稳妥。
 */
import { createRouter, createWebHashHistory } from 'vue-router'

import Dashboard from '../views/Dashboard.vue'

const routes = [
    // 根路径重定向到数据大屏
    {
        path: '/',
        redirect: '/dashboard',
    },
    {
        path: '/dashboard',
        name: 'Dashboard',
        // 路由级懒加载：首屏只加载 Dashboard，其余按需加载
        component: Dashboard,
        meta: { title: '数据大屏' },
    },
    // 兜底：未匹配的路径统一回到大屏
    {
        path: '/:pathMatch(.*)*',
        redirect: '/dashboard',
    },
]

const router = createRouter({
    history: createWebHashHistory(),
    routes,
})

// 根据路由 meta 动态设置浏览器标签标题
router.afterEach((to) => {
    const base = '全国旅游数据分析与可视化系统'
    const title = to.meta && to.meta.title
    document.title = title ? `${title} - ${base}` : base
})

export default router
