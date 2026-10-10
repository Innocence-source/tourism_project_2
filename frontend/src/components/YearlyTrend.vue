<template>
    <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
/**
 * 年度趋势双 Y 轴折线图
 * ====================
 * 数据来源：GET /api/tourism/yearly-trend/
 * 返回：[{ year, visitor, revenue }, ...]（按年份升序）
 *
 * 视觉设计（与需求文档一致）：
 *   左 Y 轴 → 接待游客（万人次）
 *   右 Y 轴 → 旅游收入（亿元）
 *
 * 为什么要双轴：客流与收入的量级相差约一个数量级（如 10 亿人次 vs 1 万亿元），
 * 放在同一根轴上会把其中一条线压成近似水平直线，看不出趋势。
 */
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { getYearlyTrend } from '@/api/tourism'
import {
    COLORS,
    EMPTY_OPTION,
    THEME_NAME,
    echarts,
    fmt,
} from '@/utils/echartsTheme'

const props = defineProps({
    /** 省份 id；不传则由后端返回收入最高省的数据 */
    regionId: { type: Number, default: null },
    /** 省份名，仅用于提示与图例说明 */
    regionName: { type: String, default: '' },
})

const chartRef = ref(null)
let chart = null

/* ==================== 构建 option ==================== */
function buildOption(list) {
    if (!list || list.length === 0) {
        return { ...EMPTY_OPTION }
    }

    const years = list.map((d) => d.year)
    const visitors = list.map((d) => (typeof d.visitor === 'number' ? d.visitor : null))
    const revenues = list.map((d) => (typeof d.revenue === 'number' ? d.revenue : null))

    // 需求文档要求：标题居中、16px
    const titleText = props.regionName ? `${props.regionName} 年度趋势` : '年度趋势'

    return {
        title: {
            text: titleText,
            left: 'center',
            top: 4,
            textStyle: { color: COLORS.text, fontSize: 16, fontWeight: 'normal' },
        },
        tooltip: {
            trigger: 'axis',
            formatter: (params) => {
                const head = `${params[0].axisValue} 年`
                const lines = params.map(
                    (it) => `${it.marker}${it.seriesName}：${fmt(it.value, 2)}`
                )
                return [head, ...lines].join('<br/>')
            },
        },
        legend: {
            top: 4,
            right: 8,
            itemWidth: 12,
            itemHeight: 8,
            textStyle: { color: COLORS.textSub, fontSize: 11 },
        },
        grid: { left: 8, right: 8, top: 40, bottom: 6, containLabel: true },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: years,
            axisLabel: { color: COLORS.textSub, fontSize: 11 },
            axisLine: { lineStyle: { color: COLORS.axisLine } },
            axisTick: { show: false },
        },
        yAxis: [
            {
                type: 'value',
                name: '万人次',
                nameTextStyle: { color: COLORS.textDim, fontSize: 11 },
                position: 'left',
                axisLabel: { color: COLORS.textSub, fontSize: 11 },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { lineStyle: { color: COLORS.splitLine } },
                scale: true,
            },
            {
                type: 'value',
                name: '亿元',
                nameTextStyle: { color: COLORS.textDim, fontSize: 11 },
                position: 'right',
                axisLabel: { color: COLORS.textSub, fontSize: 11 },
                axisLine: { show: false },
                axisTick: { show: false },
                // 右轴不画网格线，避免与左轴网格重叠造成视觉噪音
                splitLine: { show: false },
                scale: true,
            },
        ],
        series: [
            {
                name: '接待游客',
                type: 'line',
                yAxisIndex: 0,
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                lineStyle: { width: 2, color: COLORS.primary },
                itemStyle: { color: COLORS.primary },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(64, 158, 255, 0.35)' },
                        { offset: 1, color: 'rgba(64, 158, 255, 0.02)' },
                    ]),
                },
                data: visitors,
            },
            {
                name: '旅游收入',
                type: 'line',
                yAxisIndex: 1,
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                lineStyle: { width: 2, color: COLORS.accent },
                itemStyle: { color: COLORS.accent },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(145, 204, 117, 0.3)' },
                        { offset: 1, color: 'rgba(145, 204, 117, 0.02)' },
                    ]),
                },
                data: revenues,
            },
        ],
    }
}

/* ==================== 数据加载 ==================== */
async function load() {
    if (!chart) return

    try {
        const params = {}
        if (props.regionId !== null && props.regionId !== undefined) {
            params.region_id = props.regionId
        }
        const list = await getYearlyTrend(params)
        chart.setOption(buildOption(list), true)
    } catch (e) {
        console.error('[YearlyTrend] 加载失败', e)
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

watch(() => [props.regionId], load)

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
