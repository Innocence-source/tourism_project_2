<template>
    <div class="dashboard-screen">

        <!-- ==================== 顶部标题栏 ==================== -->
        <header class="dash-header">
            <!-- 左侧占位，让标题在视觉上居中 -->
            <div class="header-side header-left"></div>

            <h1 class="dash-title">全国旅游数据分析与可视化系统</h1>

            <div class="header-side header-right">
                <span class="year-label">统计年份</span>
                <select v-model.number="currentYear" class="year-select">
                    <option v-for="y in years" :key="y" :value="y">{{ y }} 年</option>
                </select>
            </div>
        </header>

        <!-- ==================== 可选条件加载异常提示 ==================== -->
        <div v-if="errorMsg" class="error-bar">
            <span class="error-icon">!</span>
            {{ errorMsg }}
            <button class="error-retry" @click="loadMeta">重试</button>
        </div>

        <!-- ==================== 关键指标卡片（4 张） ==================== -->
        <section class="summary-row">
            <SummaryCard :year="currentYear"/>
        </section>

        <!-- ==================== 图表区（三栏布局） ==================== -->
        <main class="chart-grid">

            <!-- 左栏：年度趋势 + 节假日对比 -->
            <div class="grid-col grid-col-left">
                <section class="panel">
                    <h3 class="panel-title">年度趋势</h3>
                    <div class="panel-body">
                        <YearlyTrend :region-id="trendRegionId" :region-name="trendRegionName"/>
                    </div>
                </section>
                <section class="panel">
                    <h3 class="panel-title">节假日对比</h3>
                    <div class="panel-body">
                        <HolidayCompare :year="currentYear"/>
                    </div>
                </section>
            </div>

            <!-- 中栏：中国地图热力 -->
            <div class="grid-col grid-col-center">
                <section class="panel panel-full">
                    <h3 class="panel-title">全国旅游客流分布</h3>
                    <div class="panel-body">
                        <MapHeatmap :year="currentYear" stat-type="annual"/>
                    </div>
                </section>
            </div>

            <!-- 右栏：城市排名 + 人均消费散点 -->
            <div class="grid-col grid-col-right">
                <section class="panel">
                    <h3 class="panel-title">城市客流排名 TOP10</h3>
                    <div class="panel-body">
                        <CityRanking :limit="10"/>
                    </div>
                </section>
                <section class="panel">
                    <h3 class="panel-title">人均消费分布</h3>
                    <div class="panel-body">
                        <PerCapitaScatter :year="currentYear" stat-type="annual"/>
                    </div>
                </section>
            </div>

        </main>
    </div>
</template>

<script setup>
/**
 * 数据大屏主页
 * ===========
 * 本组件只负责三件事，其余全部下沉到子组件：
 *   1. 整屏自适应（autofit.js，1920x1080 设计稿）
 *   2. 维护全局筛选状态 currentYear，并把年份下发给各图表组件
 *   3. 布局骨架（顶部标题栏 / 指标卡行 / 三栏图表区）
 *
 * 数据获取的职责划分：
 *   - 各子组件自行调用自己对应的 API（接收 year 等 prop 后自行请求并渲染），
 *     这样每个组件是自治的，增删图表不需要改动父组件的数据逻辑；
 *   - 父组件只额外调用一次 /api/tourism/meta/，用于填充年份下拉框，
 *     并决定「年度趋势」面板默认展示哪个省份。
 *
 * 年份切换的刷新机制：
 *   currentYear 变化 → 各子组件内部 watch 到 prop 变化 → 各自重新请求 → 各自 setOption。
 *   因此父组件无需手动协调刷新。
 */
import { onMounted, onUnmounted, ref } from 'vue'
import autofit from 'autofit.js'

import { getMeta } from '@/api/tourism'

import SummaryCard from '@/components/SummaryCard.vue'
import YearlyTrend from '@/components/YearlyTrend.vue'
import HolidayCompare from '@/components/HolidayCompare.vue'
import MapHeatmap from '@/components/MapHeatmap.vue'
import CityRanking from '@/components/CityRanking.vue'
import PerCapitaScatter from '@/components/PerCapitaScatter.vue'

/* ==================== 响应式状态 ==================== */
const years = ref([])              // 年份下拉候选（来自 meta 接口）
const currentYear = ref(null)      // 当前选中年份，向下透传给各图表
const errorMsg = ref('')

// 「年度趋势」面板默认展示的省份
const trendRegionId = ref(null)
const trendRegionName = ref('')

/* ==================== 加载可选条件 ==================== */
async function loadMeta() {
    errorMsg.value = ''
    try {
        const meta = await getMeta()

        years.value = meta.years || []
        // 默认年份优先取后端建议值（库中最新的年份），其次取列表首项
        currentYear.value = meta.default_year ?? (years.value[0] ?? null)

        // 年度趋势面板默认展示列表中的第一个省份。
        // 说明：provinces 由后端按 id 升序返回，而 id 顺序即导入顺序（按 2024 年客流降序），
        // 因此这里拿到的是客流第一的省份。若希望展示「收入第一省」，
        // 可改为读取 summary 接口的 top_province（本组件为减少请求未采用）。
        const provinces = meta.provinces || []
        if (provinces.length > 0) {
            trendRegionId.value = provinces[0].id
            trendRegionName.value = provinces[0].name
        }
    } catch (e) {
        errorMsg.value = `加载可选条件失败：${e.message}`
    }
}

/* ==================== 生命周期 ==================== */
onMounted(async () => {
    // 按 1920x1080 设计稿整屏缩放。
    // ⚠️ autofit.js 3.x 的参数名是 el / dw / dh，
    //    不是 2.x 的 renderDom / designWidth / designHeight（传错不报错，会静默退化）。
    autofit.init({
        el: '#app',
        dw: 1920,
        dh: 1080,
        resize: true,
        cssMode: 'scale',
    })

    await loadMeta()
})

onUnmounted(() => {
    // 释放 autofit 绑定的 resize 监听
    autofit.off()
})
</script>

<style scoped>
/* ==================== 整体屏幕 ==================== */
/* 固定为设计稿尺寸，由 autofit.js 统一缩放 */
.dashboard-screen {
    position: relative;
    width: 1920px;
    height: 1080px;
    padding: 0 20px 20px;
    background: #0b1a3a;
    /* 顶部一层淡淡的径向光晕，增强科技感 */
    background-image:
        radial-gradient(ellipse 80% 50% at 50% 0%, rgba(64, 158, 255, 0.14), transparent 70%);
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
}

/* ==================== 顶部标题栏 ==================== */
.dash-header {
    display: flex;
    align-items: center;
    height: 72px;
    flex: 0 0 72px;
    border-bottom: 1px solid #1e3a8a;
    margin-bottom: 16px;
}

.header-side {
    flex: 1 1 0;
    display: flex;
    align-items: center;
}

.header-right {
    justify-content: flex-end;
    gap: 10px;
}

.dash-title {
    flex: 0 0 auto;
    font-size: 32px;
    font-weight: 700;
    letter-spacing: 4px;
    color: #ffffff;
    text-shadow: 0 0 18px rgba(64, 158, 255, 0.75);
    white-space: nowrap;
}

.year-label {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.65);
}

.year-select {
    min-width: 130px;
    padding: 6px 12px;
    font-size: 14px;
    color: #ffffff;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid #1e3a8a;
    border-radius: 4px;
    outline: none;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.year-select:hover,
.year-select:focus {
    border-color: #409eff;
    box-shadow: 0 0 10px rgba(64, 158, 255, 0.4);
}

/* 下拉选项在部分浏览器里由系统绘制，需单独设底色避免白底黑字 */
.year-select option {
    background: #0b1a3a;
    color: #ffffff;
}

/* ==================== 异常提示条 ==================== */
.error-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    padding: 8px 14px;
    font-size: 13px;
    color: #ee6666;
    background: rgba(238, 102, 102, 0.1);
    border: 1px solid rgba(238, 102, 102, 0.45);
    border-radius: 4px;
}

.error-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    font-size: 12px;
    font-weight: 700;
    color: #0b1a3a;
    background: #ee6666;
    border-radius: 50%;
}

.error-retry {
    margin-left: auto;
    padding: 3px 12px;
    font-size: 12px;
    color: #ffffff;
    background: transparent;
    border: 1px solid #ee6666;
    border-radius: 3px;
    cursor: pointer;
}

.error-retry:hover {
    background: rgba(238, 102, 102, 0.2);
}

/* ==================== 指标卡行 ==================== */
/* 高度固定，SummaryCard 内部按 100% 撑满 */
.summary-row {
    flex: 0 0 118px;
    margin-bottom: 16px;
    min-height: 0;
}

/* ==================== 图表三栏布局 ==================== */
.chart-grid {
    display: grid;
    grid-template-columns: 1fr 1.35fr 1fr;
    gap: 16px;
    flex: 1 1 auto;
    min-height: 0;
}

.grid-col {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-height: 0;
}

/* 左、右栏各两个面板平分高度 */
.grid-col-left .panel,
.grid-col-right .panel {
    flex: 1 1 0;
    min-height: 0;
}

/* 中栏一个面板占满 */
.panel-full {
    flex: 1 1 auto;
    min-height: 0;
}

/* ==================== 面板 ==================== */
.panel {
    display: flex;
    flex-direction: column;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid #1e3a8a;
    border-radius: 6px;
    overflow: hidden;
}

.panel-title {
    flex: 0 0 auto;
    padding: 10px 0;
    font-size: 16px;
    font-weight: 500;
    color: #ffffff;
    text-align: center;
    letter-spacing: 1px;
    border-bottom: 1px solid rgba(30, 58, 138, 0.75);
}

.panel-body {
    flex: 1 1 auto;
    min-height: 0;
    padding: 8px;
    /* ECharts 容器以此为参照，故必须是定位上下文 */
    position: relative;
}
</style>
