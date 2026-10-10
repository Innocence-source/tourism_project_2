<template>
    <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
/**
 * 节假日对比分组柱状图
 * ====================
 * 数据来源：GET /api/tourism/holiday-compare/
 * 后端返回结构：{ "广东省": { national_day, spring_festival, labor_day }, ... }
 *
 * 该结构以省份名为对象的 key，字典序不稳定，因此本组件会先按
 * 「三假期客流合计」降序重排，保证 X 轴顺序符合直觉（热门省份在前）。
 *
 * 配色遵循需求文档：国庆 #5470c6 / 春节 #ee6666 / 五一 #fac858
 */
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { getHolidayCompare } from '@/api/tourism'
import {
    COLORS,
    COMMON_GRID,
    COMMON_TITLE,
    EMPTY_OPTION,
    HOLIDAY_COLORS,
    HOLIDAY_LABELS,
    THEME_NAME,
    echarts,
    fmt,
} from '@/utils/echartsTheme'

const props = defineProps({
    year: { type: Number, default: null },
    /** 取值口径：visitor_count（万人次，默认）或 revenue（亿元） */
    metric: { type: String, default: 'visitor_count' },
})

const chartRef = ref(null)
let chart = null

const METRIC_UNIT = { visitor_count: '万人次', revenue: '亿元' }
// 系列展示顺序：国庆 → 春节 → 五一
const HOLIDAY_ORDER = ['national_day', 'spring_festival', 'labor_day']

/* ==================== 构建 option ==================== */
function buildOption(raw) {
    const unit = METRIC_UNIT[props.metric] || ''

    const provinces = raw ? Object.keys(raw) : []
    if (provinces.length === 0) {
        return { ...EMPTY_OPTION }
    }

    // 按三假期合计降序排列省份，避免依赖对象 key 的字典序
    const totalOf = (p) => HOLIDAY_ORDER.reduce((sum, key) => {
        const v = raw[p] ? raw[p][key] : null
        return sum + (typeof v === 'number' ? v : 0)
    }, 0)
    provinces.sort((a, b) => totalOf(b) - totalOf(a))

    const series = HOLIDAY_ORDER.map((key) => ({
        name: HOLIDAY_LABELS[key],
        type: 'bar',
        barMaxWidth: 14,
        // 分组柱状图：同一省份下三根柱子并排
        itemStyle: {
            color: HOLIDAY_COLORS[key],
            borderRadius: [2, 2, 0, 0],
        },
        emphasis: { focus: 'series' },
        data: provinces.map((p) => {
            const v = raw[p] ? raw[p][key] : null
            return typeof v === 'number' ? v : 0
        }),
    }))

    return {
        title: { ...COMMON_TITLE, text: '' },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params) => {
                const head = params[0] ? params[0].axisValue : ''
                const lines = params.map(
                    (it) => `${it.marker}${it.seriesName}：${fmt(it.value, 2)} ${unit}`
                )
                return [head, ...lines].join('<br/>')
            },
        },
        legend: {
            top: 4,
            right: 8,
            itemWidth: 10,
            itemHeight: 8,
            textStyle: { color: COLORS.textSub, fontSize: 11 },
        },
        grid: { ...COMMON_GRID, top: 34, bottom: 6, left: 6, right: 10 },
        xAxis: {
            type: 'category',
            data: provinces,
            axisLabel: {
                color: COLORS.textSub,
                fontSize: 11,
                // 需求文档要求：X 轴省份旋转 30°
                rotate: 30,
                interval: 0,
            },
            axisLine: { lineStyle: { color: COLORS.axisLine } },
            axisTick: { show: false },
        },
        yAxis: {
            type: 'value',
            name: unit,
            nameTextStyle: { color: COLORS.textDim, fontSize: 11 },
            axisLabel: { color: COLORS.textSub, fontSize: 11 },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { lineStyle: { color: COLORS.splitLine } },
        },
        series,
    }
}

/* ==================== 数据加载 ==================== */
async function load() {
    if (!chart) return
    if (props.year === null || props.year === undefined) return

    try {
        const data = await getHolidayCompare({ year: props.year, metric: props.metric })
        chart.setOption(buildOption(data), true)
    } catch (e) {
        console.error('[HolidayCompare] 加载失败', e)
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

watch(() => [props.year, props.metric], load)

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
