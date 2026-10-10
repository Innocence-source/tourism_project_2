# 全国旅游数据分析与可视化系统

> 本科毕业设计 —— 基于 Django 的全国旅游数据分析与可视化系统设计与实现

一个前后端分离的旅游数据可视化大屏系统：后端负责数据采集、清洗、存储与聚合分析，
前端以 1920×1080 设计稿渲染可视化大屏。

---

## 一、项目简介

系统围绕「旅游统计数据」这一主题，实现了完整的 **采集 → 存储 → 分析 → 可视化** 链路：

| 环节 | 实现方式 |
|---|---|
| 数据采集 | Django management command + requests + BeautifulSoup 解析文旅厅公报表格，失败自动回落示例数据 |
| 数据存储 | MySQL 8.0，四张业务表（region / tourism_stat / city_ranking / crawl_log） |
| 数据分析 | Django ORM 聚合（values / annotate / Sum / Avg），7 个看板接口 + 2 个增值接口 |
| 可视化 | Vue3 + ECharts 5 大屏，6 个图表组件，支持年份切换与整屏自适应 |
| 数据管理 | Django Admin 后台，可查看与编辑数据；爬虫日志只读留痕 |

**关于数据的说明**：仓库内的 `backend/data/sample_data.json` 是**示例数据**，
用于在没有真实爬取数据时保证系统可演示。其 2024 年各省基准值取自各省文旅厅 / 省政府
公开口径的公开数据，其余年份按全国趋势系数外推；假期数据为**按比例估算**。
文件中已通过 `note` / `disclaimer` / `holiday_note` 字段明确标注，
**不得用于任何统计引用或对外发布**。

---

## 二、技术栈

| 层级 | 技术 | 实际版本 |
|---|---|---|
| 后端框架 | Django | 4.2.30 |
| 接口框架 | Django REST Framework | 3.15.2 |
| 数据库 | MySQL | 8.0.35 |
| 数据库驱动 | **PyMySQL**（非 mysqlclient） | 1.2.3 |
| 跨域 | django-cors-headers | 4.9.0 |
| 爬虫 | requests / BeautifulSoup4 / lxml | 2.34.2 / 4.15.0 / 5.4.0 |
| 数据处理 | pandas | 2.3.3 |
| 前端框架 | Vue | 3.5.43 |
| 路由 | Vue Router | 4.6.4 |
| HTTP | Axios | 1.20.0 |
| 图表 | **ECharts**（按需引入） | 5.6.0 |
| 大屏自适应 | autofit.js | 3.2.8 |
| 构建工具 | Vite | 8.3.0 |
| 运行环境 | Python 3.12.10 / Node.js 22.22.2 | — |

> 本项目刻意不引入 Redis / Celery / Elasticsearch / Docker / TypeScript / UI 组件库。

---

## 三、目录结构

```
tourism_project/
├── .gitignore
├── README.md
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .venv/                          # Python 虚拟环境（不提交）
│   ├── tourism_project/                # 项目配置
│   │   ├── __init__.py                 # PyMySQL 伪装为 MySQLdb
│   │   ├── settings.py
│   │   ├── urls.py                     # 总路由
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── common/                     # 跨应用复用（非 Django app）
│   │   │   ├── fields.py               # MySQL 精确类型字段（TINYINT / TEXT / DATETIME）
│   │   │   └── response.py             # 统一响应体 + 参数解析
│   │   ├── region/                     # 地区维度
│   │   │   ├── models.py  admin.py
│   │   │   ├── serializers.py  views.py  urls.py
│   │   │   └── migrations/
│   │   ├── tourism/                    # 旅游统计
│   │   │   ├── models.py  admin.py
│   │   │   ├── serializers.py  views.py  urls.py
│   │   │   └── migrations/
│   │   │       └── 0002_created_at_default.py   # 补 DEFAULT CURRENT_TIMESTAMP
│   │   ├── crawler/                    # 数据采集
│   │   │   ├── utils.py                # 抓取 / 清洗 / 解析 / 入库 / 日志
│   │   │   └── management/commands/
│   │   │       ├── crawl_tourism.py        # 爬虫主命令
│   │   │       └── import_sample_data.py   # 示例数据导入
│   │   └── analysis/                   # 深度分析
│   │       ├── views.py  urls.py
│   └── data/
│       ├── sample_data.json            # 示例数据（必须提交）
│       └── sample_page.html            # 演示用文旅厅公报页面
└── frontend/
    ├── .npmrc                          # 固定国内镜像源
    ├── package.json
    ├── vite.config.js                  # 开发代理 /api → 127.0.0.1:8001
    ├── index.html
    └── src/
        ├── main.js  App.vue
        ├── router/index.js
        ├── api/
        │   ├── request.js              # Axios 封装 + 响应解包
        │   └── tourism.js              # 9 个接口方法
        ├── utils/
        │   └── echartsTheme.js         # 按需引入 + 地图注册 + 主题 + 配色
        ├── assets/
        │   └── china.json              # 中国地图 GeoJSON（含港澳台及南海断续线）
        ├── components/
        │   ├── SummaryCard.vue         # 关键指标卡片
        │   ├── MapHeatmap.vue          # 中国地图热力
        │   ├── HolidayCompare.vue      # 节假日对比分组柱状图
        │   ├── CityRanking.vue         # 城市排名横向柱状图
        │   ├── PerCapitaScatter.vue    # 人均消费散点图
        │   └── YearlyTrend.vue         # 年度趋势双 Y 轴折线图
        └── views/
            └── Dashboard.vue           # 大屏主页面
```

---

## 四、环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| 操作系统 | Windows 10 / 11 | 本项目在 Windows 下开发验证 |
| Python | 3.8 ~ 3.12 | **开发环境使用 3.12.10**；Django 4.2 官方支持 3.8–3.12 |
| MySQL | 8.0 及以上 | 需支持 utf8mb4 |
| Node.js | 18 及以上 | 开发环境使用 22.22.2（Vite 8 要求 Node 20+） |
| Shell | Git Bash（推荐） | 路径写法见「常见问题」第 6 条 |

---

## 五、数据库初始化

### 1. 启动 MySQL 并创建数据库

```sql
CREATE DATABASE tourism_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 配置连接信息

编辑 `backend/tourism_project/settings.py`：

```python
DB_NAME = 'tourism_db'
DB_USER = 'root'
DB_PASSWORD = os.environ.get('TOURISM_DB_PASSWORD', '')   # 改成你的密码
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
```

### 3. 执行迁移建表

```bash
cd backend
./.venv/Scripts/python.exe manage.py migrate
```

迁移会创建 4 张业务表 + Django 内置表。迁移文件 `0002_created_at_default.py`
会为 `tourism_stat.created_at` 与 `crawl_log.crawled_at` 补上
`DEFAULT CURRENT_TIMESTAMP`（Django 的 `auto_now_add` 只在应用层生效，
数据库层面没有默认值，裸 SQL 插入会失败）。

### 4. 创建后台管理员

```bash
./.venv/Scripts/python.exe manage.py createsuperuser
```

---

## 六、后端启动步骤

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（首次）
& "D:/Program Files/Python312/python.exe" -m venv "D:/ProjectFloder/tourism_project/backend/.venv"

# 3. 安装依赖（首次）
./.venv/Scripts/python.exe -m pip install -r requirements.txt

# 4. 导入示例数据（首次）
./.venv/Scripts/python.exe manage.py import_sample_data

# 5. 启动服务（注意端口是 8001，不是默认的 8000）
./.venv/Scripts/python.exe manage.py runserver 8001
```

启动后访问：

- 接口首页示例：<http://127.0.0.1:8001/api/tourism/meta/>
- 数据管理后台：<http://127.0.0.1:8001/admin/>

> **为什么用 8001？** 本项目约定后端固定使用 8001 端口（8000 常被其他项目占用）。
> 如需更换，请同步修改 `frontend/vite.config.js` 中的 `proxy.target`。

---

## 七、前端启动步骤

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖（首次）
npm install

# 3. 启动开发服务器
npm run dev
```

启动后访问：**<http://127.0.0.1:5173>**

> 前端通过 Vite 代理把 `/api` 转发到后端 8001 端口，因此**不存在浏览器跨域问题**，
> 前端代码中直接写相对路径 `/api/tourism/...` 即可。
> 若后端未启动，页面会显示「加载失败」提示条。

### 生产构建

```bash
npm run build     # 产物输出到 dist/
npm run preview   # 本地预览构建产物
```

---

## 八、爬虫运行方式

爬虫命令为 `crawl_tourism`，支持多种用法：

```bash
cd backend

# ① 默认：抓取内置演示页面（data/sample_page.html）
#    走完整的 获取 → 解析 → 清洗 → 入库 链路，并写入采集日志
./.venv/Scripts/python.exe manage.py crawl_tourism

# ② 抓取真实的目标页面
./.venv/Scripts/python.exe manage.py crawl_tourism \
    --url "https://xxx.gov.cn/xxx.html" --province 广东省 --stat-type national_day --year 2024

# ③ 跳过网络，直接用示例数据兜底（答辩演示最稳妥）
./.venv/Scripts/python.exe manage.py crawl_tourism --sample

# ④ 清空业务表后重新抓取
./.venv/Scripts/python.exe manage.py crawl_tourism --flush

# ⑤ 导入 / 重新导入示例数据
./.venv/Scripts/python.exe manage.py import_sample_data
./.venv/Scripts/python.exe manage.py import_sample_data --flush   # 清空后导入
```

**参数一览**

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--url` | 内置演示页面 | 目标页面地址，支持 http(s) 与本地路径 |
| `--province` | 广东省 | 数据归属省份 |
| `--stat-type` | national_day | 统计口径：annual / spring_festival / national_day / labor_day |
| `--year` | 2024 | 统计年份 |
| `--sample` | — | 跳过网络，直接读 `sample_data.json` |
| `--flush` | — | 抓取前清空业务表（TRUNCATE，自增 ID 归零） |
| `--no-sleep` | — | 关闭请求间隔（默认每次请求前 sleep 1 秒） |

**内置容错机制**

1. **网络重试**：请求失败自动重试 2 次
2. **自动兜底**：抓取或解析失败时，自动回落读取 `sample_data.json` 灌库，保证系统始终有数据
3. **幂等入库**：全部使用 `update_or_create`，重复执行不会产生重复记录
4. **采集留痕**：每次执行写入 `crawl_log`（状态：success / failed / partial）

**关于目标页面的现实约束**：各省文旅厅公报存在 URL 逐年失效、正文以 PDF 附件为主、
页面结构随改版变动等问题，不适合作为唯一数据源。因此爬虫采用「可插拔解析器」设计 ——
解析规则集中在 `apps/crawler/utils.py` 的 `parse_holiday_table()` 中，
页面改版时只需调整该函数的表头映射表（`HEADER_KEYWORDS`）。

---

## 九、接口文档

**统一返回体**

```json
{ "code": 200, "msg": "success", "data": ... }
```

错误时 `code` 为业务错误码（400 参数错误 / 404 资源不存在 / 500 服务异常），
`msg` 为中文原因，`data` 为 `null`。

> 设计决策：业务错误统一使用 **HTTP 200 + body 中的 code**，
> 前端 Axios 只需判断 `code` 字段，不必区分 `then` / `catch` 两套逻辑。

### 1. 地图热力

```
GET /api/tourism/map-heatmap/
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| year | int | 否 | 默认 2024 |
| stat_type | string | 否 | 默认 annual |
| metric | string | 否 | visitor_count（客流，默认）/ revenue（收入） |

返回：`[{"name": "河南省", "value": 95927.21}, ...]`，按 value 降序。

`name` 为行政区划**全称**，与 `china.json` 的 `properties.name` 完全一致，无需映射。

### 2. 节假日对比

```
GET /api/tourism/holiday-compare/
```

参数：`year`、`metric`

返回：

```json
{
  "广东省": { "national_day": 5325.30, "spring_festival": 4514.65, "labor_day": 3121.11 },
  "...": {}
}
```

### 3. 城市排名

```
GET /api/tourism/city-ranking/
```

参数：`period`（如 `2025国庆`，不传则取库中最新周期）、`limit`（默认 10，范围 1–50）

返回：`[{"rank_no":1,"name":"成都市","visitor_count":1635.67,"revenue":188.90,"per_capita":1154.85}, ...]`

### 4. 人均消费散点

```
GET /api/tourism/per-capita-scatter/
```

参数：`year`、`stat_type`

返回：`[{"name":"广东省","visitor":87176.21,"per_capita":1228.28,"revenue":10707.71}, ...]`

> `revenue` 用于映射气泡大小，故必须返回（原始需求中的示例缺少该字段，已补齐）。

### 5. 年度趋势

```
GET /api/tourism/yearly-trend/
```

参数：`region_id`（不传则返回收入最高省）、`stat_type`

返回：`[{"year":2021,"visitor":51769.25,"revenue":6999.77}, ...]`，按年份升序。

### 6. 大屏汇总

```
GET /api/tourism/summary/
```

参数：`year`、`stat_type`

返回：

```json
{
  "year": 2024,
  "stat_type": "annual",
  "total_visitor": 1090473.67,
  "total_visitor_yi": 109.05,
  "total_revenue": 129626.62,
  "total_revenue_wanyi": 12.9627,
  "top_province": { "id": 5, "name": "四川省", "value": 17393.25,
                    "metric": "revenue", "metric_name": "旅游收入" },
  "avg_per_capita": 1188.72,
  "avg_per_capita_simple": 1179.35,
  "province_count": 12,
  "caliber": "样本省份合计",
  "note": "本系统当前仅入库部分省份数据，上述合计值为这些省份的加总..."
}
```

> ⚠️ **口径说明（重要）**：`total_visitor` / `total_revenue` 是**参与统计的省份加总**，
> **不是全国总量**。各省接待人次存在跨省重复统计，加总高于全国口径属正常现象。
> 前端卡片必须展示 `caliber` 字段做标注，不得写成「全国总客流」。
>
> `avg_per_capita` 采用**加权口径**（总收入 ÷ 总客流），
> `avg_per_capita_simple` 为各省人均的算术平均，供对照说明。

### 7. 地区列表

```
GET /api/region/list/
```

参数：`level`（1=省份，2=城市，不传返回全部）

返回：`[{"id":1,"name":"云南省","level":1,"level_name":"省份"}, ...]`

### 8. 元信息（补充接口）

```
GET /api/tourism/meta/
```

返回年份列表、统计周期列表、统计口径列表、省份列表及各自默认值，
供前端下拉框使用，避免在前端硬编码年份。

### 9. 同比增速排行（补充接口）

```
GET /api/analysis/growth-ranking/
```

参数：`year`、`metric`（yoy_revenue / yoy_visitor）、`order`（desc / asc）、`limit`

返回按同比增速排序的省份列表及全样本平均增速。

> 第 8、9 个接口不在原始需求的 7 个接口之内，属补充实现。

---

## 十、常见问题

### 1. `No module named 'MySQLdb'` 或版本校验报错

本项目使用 **PyMySQL** 而非 mysqlclient（Windows 下 mysqlclient 需 C++ 编译工具链，失败率高）。
伪装逻辑在 `backend/tourism_project/__init__.py`：

```python
pymysql.version_info = (1, 4, 6, 'final', 0)   # 必须先设版本号
pymysql.__version__ = '1.4.6'
pymysql.install_as_MySQLdb()
```

若报「mysqlclient 1.4.3 or newer is required」，说明这两行没生效，检查该文件是否被正确加载。

### 2. 端口被占用

- 后端 8001 被占用：`netstat -ano | grep ":8001"` 找到 PID 后结束该进程
- 前端 5173 被占用：`vite.config.js` 中设了 `strictPort: true`，会直接报错而**不会**静默换端口
  （静默换端口会导致代理失效却难以察觉）

### 3. `npm install` 很慢或中断

项目已在 `frontend/.npmrc` 中固定国内镜像源：

```
registry=https://registry.npmmirror.com
```

如仍慢，可临时指定：`npm install --registry=https://registry.npmmirror.com`

### 4. 页面图表不显示 / 显示「加载失败」

按顺序排查：

1. 后端是否已启动（`http://127.0.0.1:8001/api/tourism/meta/` 能否打开）
2. 数据库是否已导入数据（`manage.py import_sample_data`）
3. 浏览器控制台有无报错
4. 直接访问 `http://127.0.0.1:5173/api/tourism/summary/?year=2024` 能否返回 JSON

### 5. 地图是空白的

ECharts 5 **已移除内置地图**。本项目通过
`echarts.registerMap('china', chinaGeoJson)` 手动注册（见 `utils/echartsTheme.js`）。
若地图空白，检查：

- `src/assets/china.json` 是否存在（569 KB）
- 是否误改成了 `series.map: 'china'` 的旧写法（ECharts 5 中不生效）

### 6. Windows 下路径写法

在 Git Bash 中把路径传给 Windows 程序时：

- **正确**：`D:/ProjectFloder/...` 或 `D:\ProjectFloder\...`
- **错误**：`/d/ProjectFloder/...`

用 `/d/...` 形式创建虚拟环境会**静默失败**（命令返回 0，但不生成 `Scripts/python.exe`）。

### 7. 年份切换后部分图表空白

正常情况下 2021—2025 五个年份的年度与假期数据均齐全。
若出现空白，说明数据未完整导入，执行：

```bash
./.venv/Scripts/python.exe manage.py import_sample_data --flush
```

### 8. 图表打包体积较大

构建产物约 1.38 MB（gzip 472 KB），其中 `china.json` 地图数据占 571 KB。
ECharts 已采用按需引入（仅注册 地图/柱状/折线/散点 四种 + 必要组件），
相比全量引入节省约 390 KB。

---

## 十一、验收要点

| # | 验收项 | 验证方式 |
|---|---|---|
| 1 | 后端可启动 | `manage.py runserver 8001` 无报错 |
| 2 | 前端可启动 | `npm run dev` 无报错 |
| 3 | 大屏可访问 | 打开 <http://127.0.0.1:5173> |
| 4 | 6 个图表显示数据 | 4 张指标卡 + 地图 + 折线 + 柱状 + 横向柱 + 散点 |
| 5 | 年份切换刷新 | 切换 2021–2025，各图表数据随之变化 |
| 6 | Admin 可管理 | 登录 <http://127.0.0.1:8001/admin/> 查看/编辑数据 |
| 7 | 爬虫可运行 | `manage.py crawl_tourism` 或 `--sample` |
| 8 | 接口格式统一 | 所有接口返回 `{code, msg, data}` |
| 9 | 代码有中文注释 | 后端 34 个文件、前端 14 个文件均含中文注释 |
| 10 | README 完整 | 即本文档 |
