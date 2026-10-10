/**
 * 运行时 smoke test
 * ================
 * 目的：不依赖浏览器，验证前端模块在**运行时**能被正确加载与执行。
 *
 * 背景：vite build 只能证明「编译通过」，无法证明「运行时无错」。
 *      例如 echarts.registerTheme() 的参数结构写错，编译期不会报错，
 *      但浏览器控制台会在运行时抛异常，图表就白屏了。
 *
 * 原理：用 Vite 的 ssrLoadModule() 在 Node 里真实加载并执行模块，
 *      再显式调用其中的函数，捕获任何运行时异常。
 */
import { createServer } from 'vite'

/*
 * ⚠️ 必须先清除 HTTP 代理环境变量，否则测试结果不可信。
 *
 * 本机设置了 HTTP_PROXY / HTTPS_PROXY 指向内部代理（127.0.0.1:54590）。
 * axios 在 Node 端会自动读取这两个变量并让请求走代理，请求被拦下后返回的是
 * Vite 的 index.html 而非后端 JSON —— 会让人误判为「Vite 代理配置失效」。
 *
 * 而 curl 和 Node 原生 http 模块都不读取该变量，所以它们能正常拿到 JSON，
 * 这也正是本次排查中出现「同一个 URL、curl 成功而 axios 失败」的原因。
 *
 * 浏览器环境不适用系统代理环境变量，因此真实前端运行不受影响。
 */
for (const key of ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']) {
    delete process.env[key]
}

const results = []
function record(name, fn) {
    try {
        fn()
        results.push(['✓', name, ''])
    } catch (e) {
        results.push(['✗', name, e.message])
    }
}

const server = await createServer({
    server: { middlewareMode: true },
    logLevel: 'error',
})

try {
    /* ---------- 1. 加载配色 / 主题模块 ---------- */
    const theme = await server.ssrLoadModule('/src/utils/echartsTheme.js')

    record('加载 src/utils/echartsTheme.js', () => {
        if (!theme.COLORS || !theme.PALETTE) throw new Error('缺少 COLORS / PALETTE 导出')
    })

    record('配色符合设计规范（#0b1a3a / #409eff / #91cc75 / #1e3a8a）', () => {
        const c = theme.COLORS
        const expect = { bg: '#0b1a3a', primary: '#409eff', accent: '#91cc75', border: '#1e3a8a', text: '#ffffff' }
        for (const [k, v] of Object.entries(expect)) {
            if (c[k] !== v) throw new Error(`COLORS.${k} 期望 ${v}，实际 ${c[k]}`)
        }
    })

    record('调用 registerEchartsTheme() 不抛异常', () => {
        theme.registerEchartsTheme()
    })

    record('重复调用 registerEchartsTheme() 幂等', () => {
        theme.registerEchartsTheme()
    })

    record('假期配色与需求文档一致（国庆#5470c6 / 春节#ee6666）', () => {
        const h = theme.HOLIDAY_COLORS
        if (h.national_day !== '#5470c6') throw new Error('国庆色不符')
        if (h.spring_festival !== '#ee6666') throw new Error('春节色不符')
    })

    record('地图渐变首尾为 #e0f3ff → #0a2e6b', () => {
        const g = theme.MAP_GRADIENT
        if (g[0] !== '#e0f3ff' || g[g.length - 1] !== '#0a2e6b') throw new Error(`实际 ${g[0]} → ${g[g.length - 1]}`)
    })

    /* ---------- 2. 加载接口封装（不真正发请求，只验证模块结构） ---------- */
    const api = await server.ssrLoadModule('/src/api/tourism.js')
    record('加载 src/api/tourism.js 并导出 9 个接口方法', () => {
        const fns = ['getMapHeatmap', 'getHolidayCompare', 'getCityRanking', 'getPerCapitaScatter',
            'getYearlyTrend', 'getSummary', 'getRegionList', 'getMeta', 'getGrowthRanking']
        const missing = fns.filter((f) => typeof api[f] !== 'function')
        if (missing.length) throw new Error('缺失：' + missing.join(', '))
    })

    /* ---------- 3. 加载 echarts 本体，确认版本为 5.x ---------- */
    const echarts = await server.ssrLoadModule('echarts')
    record('echarts 主版本号为 5（需求指定 ECharts 5）', () => {
        if (!echarts.version.startsWith('5.')) throw new Error(`实际版本 ${echarts.version}`)
    })

    /* ---------- 4. 加载 autofit.js，确认对外 API 与调用方式匹配 ---------- */
    const autofitMod = await server.ssrLoadModule('autofit.js')
    record('autofit.js 暴露 init / off（3.x API，非 2.x 的 designWidth/renderDom）', () => {
        const a = autofitMod.default || autofitMod
        for (const fn of ['init', 'off']) {
            if (typeof a[fn] !== 'function') throw new Error(`缺少 ${fn}()`)
        }
    })

    /* ---------- 5. 端到端：经 Vite 代理真实请求 Django 后端 ---------- */
    // 这一步验证的是完整链路：Vite proxy 转发 → Django 路由 → ORM 聚合
    // → 统一返回体 {code,msg,data} → 前端可用的数据结构
    try {
        const axiosMod = await server.ssrLoadModule('axios')
        const http = axiosMod.default

        const resp = await http.get('http://127.0.0.1:5173/api/tourism/summary/', {
            params: { year: 2024 },
            timeout: 15000,
        })
        const res = resp.data
        if (res.code !== 200) throw new Error(`业务 code=${res.code} msg=${res.msg}`)

        const d = res.data
        // 数值必须是 number —— 若后端误用 DecimalField，这里会拿到字符串
        if (typeof d.total_visitor !== 'number') throw new Error('total_visitor 不是数字类型')
        if (typeof d.total_revenue !== 'number') throw new Error('total_revenue 不是数字类型')
        if (typeof d.avg_per_capita !== 'number') throw new Error('avg_per_capita 不是数字类型')
        if (!d.top_province || !d.top_province.name) throw new Error('缺少 top_province.name')
        if (!d.caliber) throw new Error('缺少 caliber（前端卡片的口径标注依赖它）')

        results.push(['✓',
            `端到端链路：Vite 代理 → Django → ORM，summary 取到真实数据`
            + `（收入第一省「${d.top_province.name}」，口径「${d.caliber}」，人均 ${d.avg_per_capita} 元）`, ''])
    } catch (e) {
        results.push(['✗', '端到端：经 Vite 代理请求后端失败', e.message])
    }

    /* ---------- 6. 端到端：年份切换对应的年份维度可用 ---------- */
    try {
        const axiosMod2 = await server.ssrLoadModule('axios')
        const http2 = axiosMod2.default

        const metaResp = await http2.get('http://127.0.0.1:5173/api/tourism/meta/', { timeout: 15000 })
        const meta = metaResp.data && metaResp.data.data
        if (!meta) throw new Error('响应体里没有 data 字段')

        if (!Array.isArray(meta.years) || meta.years.length < 2) {
            throw new Error(`years 异常：${JSON.stringify(meta.years)}`)
        }
        if (meta.default_year === null || meta.default_year === undefined) {
            throw new Error('缺少 default_year，年份下拉框无法初始化')
        }
        results.push(['✓', `年份下拉框数据源可用：可选 ${meta.years.join(' / ')}，默认 ${meta.default_year}`, ''])
    } catch (e) {
        results.push(['✗', '端到端：meta 接口异常', e.message])
    }

    /* ---------- 7. 中国地图是否真的注册成功（ECharts 5 无内置地图）---------- */
    try {
        const themeMod = await server.ssrLoadModule('/src/utils/echartsTheme.js')
        const mapObj = themeMod.echarts.getMap('china')
        if (!mapObj) {
            throw new Error('地图未注册 —— series.type="map" 会渲染成空白且不报错')
        }
        const features = (mapObj.geoJSON && mapObj.geoJSON.features) || []
        if (features.length < 34) {
            throw new Error(`地图要素数量异常：${features.length}（应 ≥ 34）`)
        }
        // 合规红线：地图必须包含台湾、香港、澳门
        const names = features.map((f) => f.properties && f.properties.name)
        const missing = ['台湾省', '香港特别行政区', '澳门特别行政区'].filter((n) => !names.includes(n))
        if (missing.length) {
            throw new Error(`地图缺少合规要素：${missing.join('、')}`)
        }
        results.push(['✓', `中国地图注册成功：${features.length} 个要素，含台湾/香港/澳门`, ''])

        // 配色是否与需求文档一致
        if (themeMod.MAP_GRADIENT[0] !== '#e0f3ff' || themeMod.MAP_GRADIENT[themeMod.MAP_GRADIENT.length - 1] !== '#0a2e6b') {
            throw new Error('地图渐变不符')
        }
    } catch (e) {
        results.push(['✗', '中国地图注册检查', e.message])
    }

    /* ---------- 8. 六个图表组件能否被正确编译加载 ---------- */
    const components = [
        'SummaryCard', 'MapHeatmap', 'HolidayCompare',
        'CityRanking', 'PerCapitaScatter', 'YearlyTrend',
    ]
    for (const name of components) {
        try {
            const mod = await server.ssrLoadModule(`/src/components/${name}.vue`)
            if (!mod.default) throw new Error('没有默认导出')
            results.push(['✓', `编译加载组件 ${name}.vue`, ''])
        } catch (e) {
            results.push(['✗', `编译加载组件 ${name}.vue`, e.message])
        }
    }

    /* ---------- 9. Dashboard 能否加载（含 autofit 等浏览器依赖）---------- */
    try {
        const mod = await server.ssrLoadModule('/src/views/Dashboard.vue')
        if (!mod.default) throw new Error('没有默认导出')
        results.push(['✓', '编译加载 views/Dashboard.vue', ''])
    } catch (e) {
        results.push(['✗', '编译加载 views/Dashboard.vue', e.message])
    }

    /* ------------------------------------------------------------------
     * 10. ECharts 配置语法真实渲染验证（SSR + SVG 渲染器）
     *
     * 说明：本机无法启动真实浏览器（agent-browser 报 SIGTERM），
     * 因此改用 ECharts 官方的服务端渲染能力，在 Node 里把配置真正跑一遍。
     * 它能验证的是「option 里的 API 名称与数据结构在 echarts 5.6.0 下确实有效」，
     * 例如 visualMap.inRange.color、series.type='map'、labelLayout.hideOverlap
     * 这些容易写错的写法是否成立。它**不能**替代人眼对最终视觉效果的确认。
     * ------------------------------------------------------------------ */
    try {
        const echarts = await import('echarts/core')
        const charts = await import('echarts/charts')
        const comps = await import('echarts/components')
        const features = await import('echarts/features')
        const renderers = await import('echarts/renderers')
        const fs = await import('node:fs')

        echarts.use([
            charts.MapChart, charts.BarChart, charts.LineChart, charts.ScatterChart,
            comps.GridComponent, comps.TooltipComponent, comps.VisualMapComponent,
            comps.TitleComponent, comps.LegendComponent, comps.GeoComponent,
            features.LabelLayout, features.UniversalTransition,
            renderers.SVGRenderer,
        ])

        // 注册地图（与 echartsTheme.js 中一致的逻辑）
        const geo = JSON.parse(fs.readFileSync('./src/assets/china.json', 'utf-8'))
        echarts.registerMap('china', geo)

        const MAP_GRADIENT = ['#e0f3ff', '#7ec2f3', '#3d8ee0', '#1a5fb4', '#0a2e6b']
        const render = (label, option) => {
            const chart = echarts.init(null, null, {
                renderer: 'svg', ssr: true, width: 900, height: 560,
            })
            chart.setOption(option)
            const svg = chart.renderToSVGString()
            chart.dispose()
            if (!svg || svg.length < 500) throw new Error(`${label} 渲染结果异常（${svg ? svg.length : 0} 字节）`)
            return svg.length
        }

        // (a) 地图 + 连续型 visualMap
        const sizeMap = render('地图热力', {
            tooltip: { trigger: 'item' },
            visualMap: {
                type: 'continuous', min: 0, max: 120000, calculable: true,
                inRange: { color: MAP_GRADIENT },
            },
            series: [{
                type: 'map', map: 'china', roam: true, zoom: 1.18,
                itemStyle: { areaColor: 'rgba(30,58,138,0.35)', borderColor: 'rgba(64,158,255,0.45)' },
                emphasis: { label: { show: true }, itemStyle: { areaColor: '#91cc75' } },
                data: [
                    { name: '广东省', value: 87400 }, { name: '四川省', value: 111900 },
                    { name: '江苏省', value: 108000 }, { name: '台湾省', value: 1200 },
                ],
            }],
        })
        results.push(['✓', `[SSR 渲染] 地图热力 + visualMap 连续型（SVG ${sizeMap} 字节）`, ''])

        // (b) 分组柱状图（含 X 轴 rotate 30）
        const sizeBar = render('节假日对比', {
            tooltip: { trigger: 'axis' },
            legend: { top: 4 },
            grid: { left: 8, right: 16, top: 34, bottom: 6, containLabel: true },
            xAxis: { type: 'category', data: ['云南', '四川', '江苏'], axisLabel: { rotate: 30, interval: 0 } },
            yAxis: { type: 'value' },
            series: [
                { name: '国庆', type: 'bar', itemStyle: { color: '#5470c6', borderRadius: [2, 2, 0, 0] }, data: [6792, 6714, 6480] },
                { name: '春节', type: 'bar', itemStyle: { color: '#ee6666' }, data: [6113, 6043, 5832] },
                { name: '五一', type: 'bar', itemStyle: { color: '#fac858' }, data: [4302, 4252, 4104] },
            ],
        })
        results.push(['✓', `[SSR 渲染] 分组柱状图 + X 轴旋转 30°（SVG ${sizeBar} 字节）`, ''])

        // (c) 横向柱状图（含右侧数值标签与渐变）
        const sizeRank = render('城市排名', {
            tooltip: { trigger: 'axis' },
            grid: { left: 6, right: 62, top: 10, bottom: 6, containLabel: true },
            xAxis: { type: 'value' },
            yAxis: { type: 'category', data: ['桂林', '昆明', '青岛', '南京', '杭州'] },
            series: [{
                type: 'bar', barMaxWidth: 12,
                itemStyle: {
                    borderRadius: [0, 4, 4, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: 'rgba(64,158,255,0.35)' },
                        { offset: 1, color: '#409eff' },
                    ]),
                },
                label: { show: true, position: 'right', formatter: (p) => String(p.value) },
                data: [900, 950, 980, 1050, 1080],
            }],
        })
        results.push(['✓', `[SSR 渲染] 横向柱状图 + 右侧标签 + 渐变（SVG ${sizeRank} 字节）`, ''])

        // (d) 散点图（气泡大小按收入 + hideOverlap）
        const sizeScatter = render('人均消费散点', {
            tooltip: { trigger: 'item' },
            grid: { left: 10, right: 20, top: 34, bottom: 34, containLabel: true },
            xAxis: { type: 'value', scale: true, name: '接待游客（万人次）' },
            yAxis: { type: 'value', scale: true, name: '人均消费（元）' },
            series: [{
                type: 'scatter',
                symbolSize: (d) => 10 + Math.sqrt(d[2] / 17600) * 26,
                itemStyle: { color: '#409eff', opacity: 0.72 },
                label: { show: true, position: 'top', formatter: (p) => p.data[3] },
                labelLayout: { hideOverlap: true },
                data: [
                    [113200, 1007, 11400, '云南省'],
                    [111900, 1573, 17600, '四川省'],
                    [108000, 1241, 13400, '江苏省'],
                ],
            }],
        })
        results.push(['✓', `[SSR 渲染] 散点图 + 气泡大小映射 + 标签防重叠（SVG ${sizeScatter} 字节）`, ''])

        // (e) 双 Y 轴折线图（含面积渐变）
        const sizeLine = render('年度趋势', {
            tooltip: { trigger: 'axis' },
            legend: { top: 4 },
            grid: { left: 8, right: 8, top: 40, bottom: 6, containLabel: true },
            xAxis: { type: 'category', boundaryGap: false, data: [2021, 2022, 2023, 2024, 2025] },
            yAxis: [
                { type: 'value', name: '万人次', position: 'left', scale: true },
                { type: 'value', name: '亿元', position: 'right', scale: true, splitLine: { show: false } },
            ],
            series: [
                {
                    name: '接待游客', type: 'line', yAxisIndex: 0, smooth: true,
                    lineStyle: { color: '#409eff' }, itemStyle: { color: '#409eff' },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(64,158,255,0.35)' },
                            { offset: 1, color: 'rgba(64,158,255,0.02)' },
                        ]),
                    },
                    data: [65428, 51052, 98607, 113700, 125070],
                },
                {
                    name: '旅游收入', type: 'line', yAxisIndex: 1, smooth: true,
                    lineStyle: { color: '#91cc75' }, itemStyle: { color: '#91cc75' },
                    data: [5419, 4469, 8719, 11400, 12540],
                },
            ],
        })
        results.push(['✓', `[SSR 渲染] 双 Y 轴折线图 + 面积渐变（SVG ${sizeLine} 字节）`, ''])

    } catch (e) {
        results.push(['✗', 'ECharts 配置 SSR 渲染验证', e.message])
    }

} catch (e) {
    results.push(['✗', '模块加载阶段异常', e.message])
} finally {
    await server.close()
}

console.log('=============== 运行时 Smoke Test ===============')
for (const [flag, name, err] of results) {
    console.log(`  ${flag}  ${name}`)
    if (err) console.log(`      ↳ ${err}`)
}
const failed = results.filter((r) => r[0] === '✗').length
console.log('------------------------------------------------')
console.log(`  通过 ${results.length - failed} / ${results.length}`)
process.exit(failed ? 1 : 0)
