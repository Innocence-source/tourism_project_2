<template>
    <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
/**
 * 人均消费散点图
 * ==============
 * 数据来源：GET /api/tourism/per-capita-scatter/
 * 返回：[{ name, visitor, per_capita, revenue }, ...]
 *
 * 视觉映射（与需求文档一致）：
 *   X 轴      → visitor     接待游客（万人次）
 *   Y 轴      → per_capita  人均消费（元）
 *   点的大小   → revenue     旅游收入（亿元）
 *
 * ⚠️ 注意：后端返回中同时包含 revenue，正是为了支撑「点大小按收入」这一映射。
 *    原始需求文档给出的返回示例是 [{name, visitor, per_capita}]，缺少 revenue，
 *    那样无法实现点大小映射 —— 这一点已在第三阶段接口设计时补齐。
 */
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { getPerCapitaScatter } from '@/api/tourism'
import {
    COLORS,
    EMPTY_OPTION,
    THEME_NAME,
    echarts,
    fmt,
} from '@/utils/echartsTheme'

const props = defineProps({
    year: { type: Number, default: null },
    statType: { type: String, default: 'annual' },
})

const chartRef = ref(null)
let chart = null

/* ==================== 构建 option ==================== */
function buildOption(list) {
    if (!list || list.length === 0) {
        return { ...EMPTY_OPTION }
    }

    // 找到最大收入，用于把气泡大小做归一化
    const maxRevenue = Math.max(...list.map((d) => Number(d.revenue) || 0), 1)

    // 每个点：[X 客流, Y 人均消费, 收入（供 symbolSize 使用）, 省份名（供 tooltip 使用）]
    const points = list.map((d) => [
        Number(d.visitor) || 0,
        Number(d.per_capita) || 0,
        Number(d.revenue) || 0,
        d.name,
    ])

    return {
        tooltip: {
            trigger: 'item',
            formatter: (p) => {
                const [, visitor, perCapita, revenue, name] = p.data
                return [
                    `<b>${name}</b>`,
                    `接待游客：${fmt(visitor, 2)} 万人次`,
                    `人均消费：${fmt(perCapita, 2)} 元`,
                    `旅游收入：${fmt(revenue, 2)} 亿元`,
                ].join('<br/>')
            },
        },
        grid: { left: 10, right: 20, top: 34, bottom: 34, containLabel: true },
        xAxis: {
            type: 'value',
            name: '接待游客（万人次）',
            nameLocation: 'middle',
            nameGap: 24,
            nameTextStyle: { color: COLORS.textDim, fontSize: 11 },
            axisLabel: { color: COLORS.textSub, fontSize: 11 },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { lineStyle: { color: COLORS.splitLine } },
            scale: true,     // 客流集中在高位时，不从 0 开始才能看出差异
        },
        yAxis: {
            type: 'value',
            name: '人均消费（元）',
            nameTextStyle: { color: COLORS.textDim, fontSize: 11 },
            axisLabel: { color: COLORS.textSub, fontSize: 11 },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { lineStyle: { color: COLORS.splitLine } },
            scale: true,
        },
        series: [
            {
                name: '人均消费',
                type: 'scatter',
                // 气泡半径随收入开平方增长 —— 用面积而非半径表示数值，视觉上更准确
                symbolSize: (data) => {
                    const revenue = data[2] || 0
                    return 10 + Math.sqrt(revenue / maxRevenue) * 26
                },
                itemStyle: {
                    color: COLORS.primary,
                    opacity: 0.72,
                    borderColor: '#ffffff',
                    borderWidth: 0.8,
                    shadowBlur: 10,
                    shadowColor: 'rgba(64, 158, 255, 0.5)',
                },
                emphasis: {
                    itemStyle: { color: COLORS.accent, opacity: 0.95 },
                },
                label: {
                    show: true,
                    position: 'top',
                    color: COLORS.textSub,
                    fontSize: 10,
                    formatter: (p) => p.data[4],
                },
                // 省份名密集时自动隐藏重叠标签（依赖 LabelLayout 特性，已注册）
                labelLayout: { hideOverlap: true },
                data: points,
            },
        ],
    }
}

/* ==================== 数据加载 ==================== */
async function load() {
    if (!chart) return
    if (props.year === null || props.year === undefined) return

    try {
        const list = await getPerCapitaScatter({ year: props.year, stat_type: props.statType })
        chart.setOption(buildOption(list), true)
    } catch (e) {
        console.error('[PerCapitaScatter] 加载失败', e)
        chart.setOption({ ...EMPTY_OPTION, title: { ...EMPTY_OPTION.title, text: '加载失败' } }, true)
    }
}

/* ==================== 生命周期 ==================== */
function handleResize() {
    if (chart) chart.resize()
}

onMounted(async () => {
    chart = echarts.init(chartRef.value, THEME_NAME)
    window.addEventListener('resize', handleResize)
    await load()
})

watch(() => [props.year, props.statType], load)

onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    if (chart) {
        chart.dispose()
        chart = null
    }
})
</script>

<style scoped>
.chart-container {
    width: 100%;
    height: 100%;
    min-height: 0;
}
</style>
