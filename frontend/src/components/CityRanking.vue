<template>
    <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
/**
 * 城市客流排名横向柱状图
 * ======================
 * 数据来源：GET /api/tourism/city-ranking/
 * 返回：[{ rank_no, name, visitor_count, revenue, per_capita }, ...]（已按 rank_no 升序）
 *
 * ⚠️ 一个容易踩的细节：
 *    ECharts 横向柱状图（yAxis 为 category）的类目是**自下而上**绘制的。
 *    若直接把 rank_no=1 放在数组首位，第一名会显示在**最底部**。
 *    因此这里对数组做 reverse()，让 rank_no=1 出现在顶部。
 */
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { getCityRanking } from '@/api/tourism'
import {
    COLORS,
    COMMON_GRID,
    COMMON_TITLE,
    EMPTY_OPTION,
    THEME_NAME,
    echarts,
    fmt,
} from '@/utils/echartsTheme'

const props = defineProps({
    /** 统计周期，如「2025国庆」；不传则由后端自动取最新周期 */
    period: { type: String, default: '' },
    limit: { type: Number, default: 10 },
    /** 取值口径：visitor_count（客流，默认）或 revenue（收入） */
    metric: { type: String, default: 'visitor_count' },
})

const chartRef = ref(null)
let chart = null

const METRIC_UNIT = { visitor_count: '万人次', revenue: '亿元' }
const METRIC_NAME = { visitor_count: '接待游客', revenue: '旅游收入' }

/* ==================== 构建 option ==================== */
function buildOption(list) {
    const unit = METRIC_UNIT[props.metric] || ''
    const metricName = METRIC_NAME[props.metric] || '接待游客'

    if (!list || list.length === 0) {
        return { ...EMPTY_OPTION }
    }

    // 反转，使 rank_no=1 出现在图表顶部（见文件头说明）
    const ordered = [...list].reverse()
    const cities = ordered.map((d) => d.name)
    const values = ordered.map((d) => {
        const v = d[props.metric]
        return typeof v === 'number' ? v : 0
    })

    return {
        title: { ...COMMON_TITLE, text: '' },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params) => {
                const idx = params[0].dataIndex
                const item = ordered[idx]
                return [
                    `<b>${item.name}</b>`,
                    `${metricName}：${fmt(item.visitor_count, 2)} 万人次`,
                    `旅游收入：${fmt(item.revenue, 2)} 亿元`,
                    `人均消费：${fmt(item.per_capita, 2)} 元`,
                ].join('<br/>')
            },
        },
        grid: { left: 6, right: 62, top: 10, bottom: 6, containLabel: true },
        xAxis: {
            type: 'value',
            axisLabel: { color: COLORS.textSub, fontSize: 11 },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { lineStyle: { color: COLORS.splitLine } },
        },
        yAxis: {
            type: 'category',
            data: cities,
            axisLabel: { color: COLORS.text, fontSize: 12 },
            axisLine: { lineStyle: { color: COLORS.axisLine } },
            axisTick: { show: false },
        },
        series: [
            {
                name: metricName,
                type: 'bar',
                barMaxWidth: 12,
                itemStyle: {
                    borderRadius: [0, 4, 4, 0],
                    // 由浅到深的横向渐变，配合深色背景更通透
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: 'rgba(64, 158, 255, 0.35)' },
                        { offset: 1, color: COLORS.primary },
                    ]),
                },
                emphasis: {
                    itemStyle: { color: COLORS.accent },
                },
                // 需求文档要求：数值标签显示在柱子右侧
                label: {
                    show: true,
                    position: 'right',
                    color: COLORS.text,
                    fontSize: 11,
                    formatter: (p) => fmt(p.value, 0),
                },
                data: values,
            },
        ],
    }
}

/* ==================== 数据加载 ==================== */
async function load() {
    if (!chart) return

    try {
        const params = { limit: props.limit, metric: props.metric }
        // period 为空时不传该参数，由后端返回最新周期
        if (props.period) params.period = props.period

        const list = await getCityRanking(params)
        chart.setOption(buildOption(list), true)
    } catch (e) {
        console.error('[CityRanking] 加载失败', e)
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

watch(() => [props.period, props.limit, props.metric], load)

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
