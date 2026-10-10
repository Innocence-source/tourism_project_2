/**
 * 旅游数据接口集合
 * ================
 * 与后端 apps/tourism/urls.py、apps/region/urls.py、apps/analysis/urls.py
 * 一一对应。所有方法都返回 Promise，resolve 的值已经是解包后的 data，
 * 无需再取 .data。
 *
 * 统一说明：
 *   - 客流单位：万人次
 *   - 收入单位：亿元
 *   - 人均消费单位：元
 */
import request from './request'

/* ==================== 1. 地图热力 ==================== */
/**
 * 获取地图热力数据
 * @param {Object} params
 * @param {number} params.year       年份，如 2024
 * @param {string} [params.stat_type] 统计口径：annual / spring_festival / national_day / labor_day
 * @param {string} [params.metric]   visitor_count（客流，默认）/ revenue（收入）
 * @returns {Promise<Array<{name: string, value: number}>>}
 *          name 为行政区划全称（与 china.json 的 properties.name 完全一致）
 */
export function getMapHeatmap(params) {
    return request.get('/tourism/map-heatmap/', { params })
}

/* ==================== 2. 节假日对比 ==================== */
/**
 * 获取各省节假日对比数据
 * @param {Object} params
 * @param {number} params.year
 * @param {string} [params.metric] visitor_count / revenue
 * @returns {Promise<Object>} { "广东省": { national_day, spring_festival, labor_day }, ... }
 */
export function getHolidayCompare(params) {
    return request.get('/tourism/holiday-compare/', { params })
}

/* ==================== 3. 城市排名 ==================== */
/**
 * 获取城市榜单
 * @param {Object} params
 * @param {string} [params.period] 统计周期，如 "2025国庆"；不传则后端自动取最新
 * @param {number} [params.limit]  条数，默认 10，范围 1~50
 * @returns {Promise<Array<{rank_no, name, visitor_count, revenue, per_capita}>>}
 */
export function getCityRanking(params) {
    return request.get('/tourism/city-ranking/', { params })
}

/* ==================== 4. 人均消费散点 ==================== */
/**
 * 获取人均消费散点数据
 * @param {Object} params
 * @param {number} params.year
 * @param {string} [params.stat_type]
 * @returns {Promise<Array<{name, visitor, per_capita, revenue}>>}
 *          visitor 作 X 轴，per_capita 作 Y 轴，revenue 映射气泡大小
 */
export function getPerCapitaScatter(params) {
    return request.get('/tourism/per-capita-scatter/', { params })
}

/* ==================== 5. 年度趋势 ==================== */
/**
 * 获取某省的年度趋势
 * @param {Object} params
 * @param {number} [params.region_id] 省份 id；不传则后端返回收入最高省
 * @param {string} [params.stat_type]
 * @returns {Promise<Array<{year, visitor, revenue}>>} 按年份升序
 */
export function getYearlyTrend(params) {
    return request.get('/tourism/yearly-trend/', { params })
}

/* ==================== 6. 大屏汇总 ==================== */
/**
 * 获取大屏顶部指标卡数据
 * @param {Object} params
 * @param {number} params.year
 * @param {string} [params.stat_type]
 * @returns {Promise<Object>} 含 total_visitor / total_revenue / top_province /
 *          avg_per_capita，以及口径说明字段 caliber、note
 *
 * ⚠️ 注意：total_* 是「样本省份合计」而非全国总量，
 *    前端卡片必须展示 caliber 字段做口径标注。
 */
export function getSummary(params) {
    return request.get('/tourism/summary/', { params })
}

/* ==================== 7. 地区列表 ==================== */
/**
 * 获取地区列表
 * @param {Object} [params]
 * @param {number} [params.level] 1=省份，2=城市；不传返回全部
 * @returns {Promise<Array<{id, name, level, level_name}>>}
 */
export function getRegionList(params) {
    return request.get('/region/list/', { params })
}

/* ==================== 8. 元信息（下拉框数据源） ==================== */
/**
 * 获取系统可选条件（年份 / 统计周期 / 统计口径 / 省份）
 * 用于填充页面上的各种下拉选择器，避免在前端硬编码年份。
 * @returns {Promise<{years: number[], periods: string[], stat_types: Array,
 *          provinces: Array, default_year, default_period}>}
 */
export function getMeta() {
    return request.get('/tourism/meta/')
}

/* ==================== 9. 同比增速排行（增值接口） ==================== */
/**
 * 获取同比增速排行
 * @param {Object} params
 * @param {number} params.year
 * @param {string} [params.metric] yoy_revenue（默认）/ yoy_visitor
 * @param {string} [params.order]  desc（默认）/ asc
 * @param {number} [params.limit]
 * @returns {Promise<Object>} 含 items 数组与 avg_yoy 平均增速
 */
export function getGrowthRanking(params) {
    return request.get('/analysis/growth-ranking/', { params })
}
