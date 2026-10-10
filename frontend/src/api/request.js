/**
 * Axios 实例封装
 * ==============
 *
 * 后端所有接口的统一返回体为 {code, msg, data}，且**业务错误也用 HTTP 200 返回**
 * （详见后端 apps/common/response.py 的设计说明）。因此这里在响应拦截器中统一解包：
 *
 *     code === 200  →  直接把 data 返回给业务代码
 *                      调用方写 `const list = await getMapHeatmap()` 即可拿到数组，
 *                      不需要再写 res.data.data 这种重复取值
 *     code !== 200  →  打印具体错误原因并 reject，由调用方 catch 后提示用户
 *
 * 因为开发环境已通过 Vite proxy 把 /api 转发到后端 8001 端口（同源），
 * 所以不存在浏览器跨域问题，无需配置 CORS 相关请求头。
 */
import axios from 'axios'

const service = axios.create({
    // 加 /api 前缀，配合 vite.config.js 中的 proxy 规则转发到 Django
    baseURL: '/api',
    timeout: 15000,
})

/* ==================== 请求拦截器 ==================== */
service.interceptors.request.use(
    (config) => {
        // 预留扩展位：如后续加入登录态，可在此统一注入 Authorization
        return config
    },
    (error) => Promise.reject(error)
)

/* ==================== 响应拦截器 ==================== */
service.interceptors.response.use(
    (response) => {
        const res = response.data

        // 非标准返回体（例如后端 500 时返回的 HTML 错误页）直接透传，
        // 交由调用方判断，避免在这里读属性时报错
        if (!res || typeof res !== 'object' || !('code' in res)) {
            return res
        }

        // 业务成功：直接返回 data
        if (res.code === 200) {
            return res.data
        }

        // 业务失败：打印并抛出，message 使用后端给的中文原因
        console.error(`[API 业务错误] code=${res.code}  msg=${res.msg}`)
        return Promise.reject(new Error(res.msg || `接口返回异常（code=${res.code}）`))
    },
    (error) => {
        // 网络层错误：归类出人话提示，便于排查（尤其是「后端没启动」这种最常见情况）
        let message = '网络请求失败'
        if (error.response) {
            message = `请求失败：HTTP ${error.response.status}`
        } else if (error.code === 'ECONNABORTED') {
            message = '请求超时，请确认后端服务已在 8001 端口启动'
        } else if (error.message) {
            // 后端未启动时 Axios 抛出的是 "Network Error"
            message = error.message
        }
        console.error('[API 网络错误]', message, '->', error.config && error.config.url)
        return Promise.reject(new Error(message))
    }
)

export default service
