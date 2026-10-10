/**
 * ECharts 按需引入 + 中国地图注册 + 主题与配色常量
 * ==============================================
 *
 * 【为什么用按需引入，而不是 `import * as echarts from 'echarts'`】
 * 全量引入会把所有图表类型（关系图、树图、桑基图、3D 等）全部打进包里。
 * 本系统只用到 地图 / 柱状 / 折线 / 散点 四种。
 *
 * 实测对比（本项目完整版，其中 china.json 占 571 KB）：
 *    全量引入 echarts →  构建产物 JS 1770 KB（gzip 597 KB）
 *    按需引入 echarts →  构建产物 JS 1380 KB（gzip 472 KB）
 *    净节省约 390 KB（22%）
 * 说明：包体积的大头其实是地图 GeoJSON 数据本身（571 KB），
 *      echarts 代码部分已从约 1200 KB 压到约 810 KB。
 *
 * 【为什么把地图注册也放这里】
 * ECharts 5 **已移除内置地图**。若不调用 registerMap，series.type='map'
 * 会渲染出一片空白而不报错 —— 这是本类项目最常见的翻车点。
 * 把注册逻辑与 echarts 实例放在同一模块，保证「用到 echarts 的地方一定已注册地图」，
 * 避免某个组件忘记注册导致地图空白。
 *
 * 【使用方式】
 *     import { echarts, THEME_NAME, COLORS } from '@/utils/echartsTheme'
 *     const chart = echarts.init(dom, THEME_NAME)
 *
 * 配色规范（与设计稿一致）：
 *   背景 #0b1a3a ｜ 卡片 rgba(255,255,255,0.04) ｜ 主色 #409eff
 *   强调 #91cc75 ｜ 文字 #ffffff ｜ 边框 #1e3a8a
 */
import * as echarts from 'echarts/core'

// 图表类型（只引入用得到的四种）
import { BarChart, LineChart, MapChart, ScatterChart } from 'echarts/charts'

// 组件
import {
    GridComponent,        // 直角坐标系
    LegendComponent,      // 图例
    TitleComponent,       // 标题（含「暂无数据」占位）
    TooltipComponent,     // 提示框
    VisualMapComponent,   // 地图热力所需的连续型视觉映射
    GeoComponent,         // 地理坐标系
    DatasetComponent,     // 数据集
    GraphicComponent,     // 图形元素
} from 'echarts/components'

// 特性
import { LabelLayout, UniversalTransition } from 'echarts/features'

// 渲染器（Canvas，比 SVG 更适合大数据量地图）
import { CanvasRenderer } from 'echarts/renderers'

// 中国地图 GeoJSON（569 KB，含 34 个省级行政区 + 南海断续线，离线可用）
import chinaGeoJson from '@/assets/china.json'

/* ==================== 按需注册 ==================== */
echarts.use([
    BarChart,
    LineChart,
    MapChart,
    ScatterChart,

    GridComponent,
    LegendComponent,
    TitleComponent,
    TooltipComponent,
    VisualMapComponent,
    GeoComponent,
    DatasetComponent,
    GraphicComponent,

    LabelLayout,
    UniversalTransition,

    CanvasRenderer,
])

/* ==================== 中国地图注册 ==================== */
/** 地图名称，series.map 与 geo.map 都用它 */
export const CHINA_MAP_NAME = 'china'

let mapRegistered = false

/**
 * 注册中国地图（幂等）。
 * ⚠️ ECharts 5 无内置地图，不注册则地图系列渲染为空白。
 * 地图数据中的 name 为行政区划全称（如「广东省」「广西壮族自治区」），
 * 与数据库 region.name 完全一致，无需名称映射。
 */
export function registerChinaMap() {
    if (mapRegistered) return
    echarts.registerMap(CHINA_MAP_NAME, chinaGeoJson)
    mapRegistered = true
}

// 模块加载即注册，保证任何组件拿到 echarts 时地图已就绪
registerChinaMap()

/** 主题名称，注册后传给 echarts.init(dom, THEME_NAME) */
export const THEME_NAME = 'tourismDark'

/** 全局配色常量（也供非图表元素，如指标卡、面板边框使用） */
export const COLORS = {
    bg: '#0b1a3a',
    cardBg: 'rgba(255, 255, 255, 0.04)',
    primary: '#409eff',
    accent: '#91cc75',
    text: '#ffffff',
    border: '#1e3a8a',
    // 辅助色（次级文字、坐标轴标签）
    textSub: 'rgba(255, 255, 255, 0.65)',
    textDim: 'rgba(255, 255, 255, 0.4)',
    axisLine: 'rgba(64, 158, 255, 0.25)',
    splitLine: 'rgba(64, 158, 255, 0.12)',
}

/** 图表系列通用色板 */
export const PALETTE = [
    '#409eff', // 主蓝
    '#91cc75', // 辅绿
    '#fac858', // 金黄
    '#ee6666', // 警示红
    '#73c0de', // 浅蓝
    '#5470c6', // 深蓝
    '#3ba272', // 翠绿
    '#fc8452', // 橙
    '#9a60b4', // 紫
    '#ea7ccc', // 粉
]

/** 国庆 / 春节 / 五一 三个假期的固定用色（与需求文档一致） */
export const HOLIDAY_COLORS = {
    national_day: '#5470c6',
    spring_festival: '#ee6666',
    labor_day: '#fac858',
}

/** 假期口径的中文名 */
export const HOLIDAY_LABELS = {
    national_day: '国庆',
    spring_festival: '春节',
    labor_day: '五一',
}

/** 地图热力的连续渐变（由浅到深，与需求文档一致） */
export const MAP_GRADIENT = ['#e0f3ff', '#7ec2f3', '#3d8ee0', '#1a5fb4', '#0a2e6b']

/** 图表通用 grid（留出坐标轴标签空间） */
export const COMMON_GRID = {
    left: 8,
    right: 16,
    top: 42,
    bottom: 8,
    containLabel: true,
}

/** 图表通用标题样式（居中、16px，符合需求文档要求） */
export const COMMON_TITLE = {
    text: '',
    left: 'center',
    top: 6,
    textStyle: {
        color: COLORS.text,
        fontSize: 16,
        fontWeight: 'normal',
    },
}

/** 「暂无数据」占位配置，供各图表在数据为空时复用 */
export const EMPTY_OPTION = {
    title: {
        text: '暂无数据',
        left: 'center',
        top: 'middle',
        textStyle: {
            color: COLORS.textDim,
            fontSize: 14,
            fontWeight: 'normal',
        },
    },
}

/** 千分位数字格式化（tooltip / 标签通用） */
export function fmt(value, digits = 2) {
    if (value === null || value === undefined || Number.isNaN(value)) return '--'
    return Number(value).toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    })
}

let themeRegistered = false

/**
 * 注册 ECharts 深色主题（幂等，重复调用只注册一次）
 * 使用方式：echarts.init(dom, THEME_NAME)
 */
export function registerEchartsTheme() {
    if (themeRegistered) return

    echarts.registerTheme(THEME_NAME, {
        color: PALETTE,
        backgroundColor: 'transparent',

        textStyle: {
            color: COLORS.textSub,
            fontSize: 12,
        },

        title: {
            textStyle: { color: COLORS.text, fontSize: 16 },
            subtextStyle: { color: COLORS.textSub },
        },

        legend: {
            textStyle: { color: COLORS.textSub },
            itemWidth: 12,
            itemHeight: 8,
        },

        tooltip: {
            backgroundColor: 'rgba(11, 26, 58, 0.92)',
            borderColor: COLORS.border,
            borderWidth: 1,
            textStyle: { color: COLORS.text, fontSize: 12 },
            axisPointer: {
                lineStyle: { color: COLORS.primary, opacity: 0.5 },
                crossStyle: { color: COLORS.primary, opacity: 0.5 },
            },
        },

        categoryAxis: {
            axisLine: { lineStyle: { color: COLORS.axisLine } },
            axisTick: { show: false },
            axisLabel: { color: COLORS.textSub },
            splitLine: { show: false, lineStyle: { color: COLORS.splitLine } },
        },

        valueAxis: {
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: COLORS.textSub },
            splitLine: { lineStyle: { color: COLORS.splitLine } },
        },

        // 折线图默认样式
        line: {
            smooth: true,
            symbolSize: 6,
            lineStyle: { width: 2 },
        },

        // 柱状图默认圆角
        bar: {
            itemStyle: { barBorderRadius: [4, 4, 0, 0] },
        },
    })

    themeRegistered = true
}

// 模块加载即注册主题
registerEchartsTheme()

export { echarts }

export default {
    echarts,
    THEME_NAME,
    COLORS,
    PALETTE,
    HOLIDAY_COLORS,
    HOLIDAY_LABELS,
    MAP_GRADIENT,
    COMMON_GRID,
    COMMON_TITLE,
    EMPTY_OPTION,
    CHINA_MAP_NAME,
    fmt,
    registerEchartsTheme,
    registerChinaMap,
}
