<template>
    <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
/**
 * 中国地图热力图
 * ==============
 * 数据来源：GET /api/tourism/map-heatmap/
 *
 * ⚠️ 两个必须注意的点：
 *
 * 1. ECharts 5 已移除内置地图。本组件依赖 @/utils/echartsTheme 在模块加载时
 *    执行的 echarts.registerMap('china', geoJson)。若注册缺失，
 *    series.type='map' 会渲染出一片空白且**不会报错**。
 *
 * 2. 地图要素的 name 必须与数据项的 name 完全一致才能着色。
 *    本项目 GeoJSON 的 name 是行政区划全称（「广东省」「广西壮族自治区」），
 *    数据库 region.name 也是全称，二者天然匹配，无需名称映射表。
 *    GeoJSON 中还有一个 name 为空字符串的要素（adcode=100000_JD，南海断续线），
 *    它在 tooltip 里会显示为空名，故 formatter 中做了兜底处理。
 */
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { getMapHeatmap } from '@/api/tourism'
import {
    CHINA_MAP_NAME,
    COLORS,
    COMMON_TITLE,
    EMPTY_OPTION,
    MAP_GRADIENT,
    THEME_NAME,
    echarts,
    fmt,
} from '@/utils/echartsTheme'

const props = defineProps({
    year: { type: Number, default: null },
    statType: { type: String, default: 'annual' },
    /** 取值口径：visitor_count（客流，默认）或 revenue（收入） */
    metric: { type: String, default: 'visitor_count' },
})

const chartRef = ref(null)
let chart = null

const METRIC_UNIT = { visitor_count: '万人次', revenue: '亿元' }
const METRIC_NAME = { visitor_count: '接待游客', revenue: '旅游收入' }

/* ==================== 构建 option ==================== */
function buildOption(list) {
    const metricName = METRIC_NAME[props.metric] || '接待游客'
    const unit = METRIC_UNIT[props.metric] || ''

    // 数据为空：只显示「暂无数据」，不渲染地图（否则会是一张全灰的空图）
    if (!list || list.length === 0) {
        return { ...EMPTY_OPTION, title: { ...EMPTY_OPTION.title, text: '暂无数据' } }
    }

    // visualMap 的上界取实际最大值，避免个别极高值把其余省份压成一片浅色
    const maxValue = Math.max(...list.map((d) => Number(d.value) || 0))

    return {
        title: { ...COMMON_TITLE, text: '' },
        tooltip: {
            trigger: 'item',
            formatter: (params) => {
                // 南海断续线要素的 name 为空，给个兜底显示
                const name = params.name && params.name.trim() ? params.name : '南海诸岛'
                const val = params.value
                const text = val === undefined || val === null || Number.isNaN(val)
                    ? '暂无数据'
                    : `${fmt(val, 2)} ${unit}`
                return `${name}<br/>${metricName}：${text}`
            },
        },
        visualMap: {
            type: 'continuous',
            min: 0,
            max: maxValue,
            left: 10,
            bottom: 10,
            itemWidth: 12,
            itemHeight: 90,
            text: ['高', '低'],
            calculable: true,
            inRange: { color: MAP_GRADIENT },
            textStyle: { color: COLORS.textSub, fontSize: 11 },
        },
        series: [
            {
                name: metricName,
                type: 'map',
                map: CHINA_MAP_NAME,
                roam: true,          // 允许滚轮缩放与拖拽平移，便于查看小省份
                zoom: 1.18,
                scaleLimit: { min: 1, max: 4 },
                label: { show: false },
                itemStyle: {
                    // 无数据省份的底色（比背景略亮，保证轮廓可见）
                    areaColor: 'rgba(30, 58, 138, 0.35)',
                    borderColor: 'rgba(64, 158, 255, 0.45)',
                    borderWidth: 0.8,
                },
                emphasis: {
                    label: { show: true, color: '#ffffff', fontSize: 12 },
                    itemStyle: {
                        areaColor: COLORS.accent,
                        borderColor: '#ffffff',
                        borderWidth: 1.2,
                    },
                },
                select: { disabled: true },
                data: list,
            },
        ],
    }
}

/* ==================== 数据加载 ==================== */
async function load() {
    if (!chart) return
    if (props.year === null || props.year === undefined) return

    try {
        const list = await getMapHeatmap({
            year: props.year,
            stat_type: props.statType,
            metric: props.metric,
        })
        chart.setOption(buildOption(list), true)
    } catch (e) {
        console.error('[MapHeatmap] 加载失败', e)
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

watch(() => [props.year, props.statType, props.metric], load)

onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    // 必须 dispose，否则热更新时会残留实例，造成内存泄漏与控制台警告
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
