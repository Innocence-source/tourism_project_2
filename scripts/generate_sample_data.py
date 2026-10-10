# -*- coding: utf-8 -*-
"""
生成 backend/data/sample_data.json

设计原则：
    1. 各指标的绝对量级参照公开统计公报的公开口径量级构造（非真实统计数据）；
    2. 使用固定随机种子，保证每次生成结果完全一致、可复现；
    3. 三条指标自洽：revenue = visitor_count × per_capita ÷ 10000；
    4. 同比增速由相邻年份实际数值反推，不由人工编造，避免出现"数据打架"。
"""
import json
import random
import os

SEED = 20260924
random.seed(SEED)


def jitter(value, pct=0.03):
    """在 value 基础上施加 ±pct 的随机扰动，让数据看起来不像等比缩放出来的。"""
    return value * (1 + random.uniform(-pct, pct))


# ============================================================
# 1. 省份与城市基础数据
#    字段：省份名, 经度, 纬度, 2024年客流(万人次), 2024年收入(亿元), [城市(名, 经度, 纬度)]
#
#    ⚠️ 2024 年基准值取自各省文旅厅 / 省政府公开口径（2024 年度数据），
#       主要来源：
#         江苏 10.8 亿人次 / 1.34 万亿元      云南 11.32 亿人次 / 1.14 万亿元
#         四川 11.19 亿人次 / 1.76 万亿元     河南 超 10 亿人次 / 超 1 万亿元
#         广西 9.62 亿人次 / 1.03 万亿元      山东 9 亿人次 / 超 1 万亿元
#         广东 8.74 亿人次 / 1.1 万亿元       浙江 超 8 亿人次 / 1.24 万亿元
#         湖南 7.42 亿人次 / 1.06 万亿元      湖北 8.38 亿人次（收入为推算）
#         陕西 8.17 亿人次（收入为推算）       福建 6.5 亿人次（收入为推算）
#       标注「推算」的省份因公开报道未披露收入，按全国人均消费中位数
#       （约 1111 元/人次，公开统计口径）反算得到。
# ============================================================
PROVINCES = [
    ("云南省", 102.712251, 25.040609, 113200, 11400, [
        ("昆明市", 102.712251, 25.040609),
        ("大理市", 100.225668, 25.589449),
        ("丽江市", 100.233026, 26.872108),
    ]),
    ("四川省", 104.065735, 30.659462, 111900, 17600, [
        ("成都市", 104.065735, 30.659462),
        ("绵阳市", 104.741722, 31.464020),
        ("乐山市", 103.761263, 29.582024),
    ]),
    ("江苏省", 118.767413, 32.041544, 108000, 13400, [
        ("南京市", 118.796877, 32.060255),
        ("苏州市", 120.619585, 31.299379),
        ("无锡市", 120.301663, 31.574729),
    ]),
    ("河南省", 113.665412, 34.757975, 100000, 10000, [
        ("郑州市", 113.625368, 34.746599),
        ("洛阳市", 112.434468, 34.663041),
        ("开封市", 114.341447, 34.797049),
    ]),
    ("广西壮族自治区", 108.320004, 22.824020, 96200, 10300, [
        ("南宁市", 108.320004, 22.824020),
        ("桂林市", 110.299121, 25.274215),
        ("北海市", 109.119254, 21.473343),
    ]),
    ("山东省", 117.000923, 36.675807, 90000, 10000, [
        ("济南市", 117.000923, 36.675807),
        ("青岛市", 120.355173, 36.082982),
        ("烟台市", 121.391382, 37.539297),
    ]),
    ("广东省", 113.280637, 23.125178, 87400, 11000, [
        ("广州市", 113.264434, 23.129162),
        ("深圳市", 114.057868, 22.543099),
        ("珠海市", 113.576726, 22.270715),
    ]),
    ("湖北省", 114.298572, 30.584355, 83800, 8800, [
        ("武汉市", 114.298572, 30.584355),
        ("宜昌市", 111.290843, 30.702636),
        ("襄阳市", 112.144146, 32.042426),
    ]),
    ("陕西省", 108.948024, 34.263161, 81700, 7350, [
        ("西安市", 108.948024, 34.263161),
        ("咸阳市", 108.705117, 34.333439),
        ("宝鸡市", 107.144870, 34.369315),
    ]),
    ("浙江省", 120.153576, 30.287459, 80000, 12400, [
        ("杭州市", 120.153576, 30.287459),
        ("宁波市", 121.549792, 29.868388),
        ("温州市", 120.672111, 28.000575),
    ]),
    ("湖南省", 112.982279, 28.194090, 74200, 10600, [
        ("长沙市", 112.982279, 28.194090),
        ("张家界市", 110.479921, 29.127401),
        ("岳阳市", 113.132855, 29.370291),
    ]),
    ("福建省", 119.306239, 26.075302, 65000, 7020, [
        ("福州市", 119.306239, 26.075302),
        ("厦门市", 118.110220, 24.490474),
        ("泉州市", 118.589459, 24.908853),
    ]),
]

# ============================================================
# 2. 年度系数（相对 2024 年，基准年为 2024）
#    校准依据（公开统计趋势，非杜撰）：
#        全国国内旅游人次  2022 年较 2021 年约 -22%，2023 年约 +93%，2024 年约 +15%
#        全国国内旅游花费  2024 年约 +17%（快于人次，因人均消费上升约 2%）
#    故 2024/2023 = 1.148 -> 2023 = 0.871；2023/2022 = 1.93 -> 2022 = 0.451；
#       2022/2021 = 0.78 -> 2021 = 0.578
# ============================================================
YEAR_FACTOR = {2021: 0.578, 2022: 0.451, 2023: 0.871, 2024: 1.00, 2025: 1.10}

# 人均消费年度系数（相对 2024 年）
# 说明：人均消费的波动远小于客流 —— 2022 年小幅下滑后逐年回升，年增幅约 2%。
#      收入由「客流 x 人均」推导，因此收入增速自然快于客流增速，符合真实规律。
PER_CAPITA_YEAR_FACTOR = {2021: 0.93, 2022: 0.91, 2023: 0.98, 2024: 1.00, 2025: 1.02}

# ============================================================
# 3. 节假日系数
#    校准依据：7 个省份 2024 年春节的官方口径数据（万人次 / 亿元）
#        广东 7606.9 / 693.6     江苏 5548.18 / 441.24    四川 6047.82 / 309.93
#        河南 5021.6 / 297.7     浙江 3032.6 / 437.6      湖南 3686.17 / 651.61
#        福建 3257.47 / 277.18
#    由此得到「春节客流 / 年度客流」约 5.0%~5.4%（广东因反向过年特殊，达 8.7%），
#    「春节人均 / 年度人均」约 0.5~1.2 倍，均值约 0.75。
#    国庆假期更长、长途出行更多，占比与人均均略高于春节；五一假期最短。
# ============================================================
# 假期客流占该省年度客流的比例
HOLIDAY_VISITOR_RATIO = {
    'national_day': 0.060,      # 国庆
    'spring_festival': 0.054,   # 春节
    'labor_day': 0.038,         # 五一
}
# 假期人均消费相对该省年度人均消费的倍数
HOLIDAY_PER_CAPITA_RATIO = {
    'national_day': 0.90,
    'spring_festival': 0.80,
    'labor_day': 0.75,
}
# 参与生成的假期年份
# 说明：刻意与年度数据保持同一批年份（2021—2025），
#      否则前端年份下拉框提供 5 个年份，用户切到 2021—2023 时
#      节假日对比 / 人均散点会显示「暂无数据」，容易被误认为系统故障。
HOLIDAY_YEARS = (2021, 2022, 2023, 2024, 2025)

STAT_TYPE_CN = {
    'annual': '年度',
    'national_day': '国庆',
    'spring_festival': '春节',
    'labor_day': '五一',
}

DATA_SOURCE_HINT = '示例数据（按公开统计公报量级构造，非真实采集结果）'


# ============================================================
# 4. 生成地区数据
# ============================================================
regions = []
for prov_name, lng, lat, _v, _r, cities in PROVINCES:
    regions.append({
        'name': prov_name,
        'level': 1,
        'parent': None,
        'longitude': lng,
        'latitude': lat,
        'cities': [
            {'name': c[0], 'level': 2, 'longitude': c[1], 'latitude': c[2]}
            for c in cities
        ],
    })


# ============================================================
# 5. 生成年度统计（2021—2025）
# ============================================================
stats = []
prov_annual = {}          # {省名: {年: (客流, 收入, 人均)}}
for prov_name, _lng, _lat, base_v, base_r, _cities in PROVINCES:
    prov_annual[prov_name] = {}
    base_per_capita = base_r * 10000.0 / base_v      # 该省 2024 年人均消费基准
    for year, factor in YEAR_FACTOR.items():
        # 客流按年度系数缩放。
        # 扰动刻意压到 ±1%：同比是由相邻年份作比得出的，
        # 若单年扰动 ±3%，同比误差会被放大到 ±6%，导致 2024 年增速
        # 从设定的 +14.8% 漂到 +19%，与公开口径明显不符。
        v = jitter(base_v * factor, 0.01)
        # 人均消费独立缩放（波动远小于客流），收入由二者推导 —— 三指标天然自洽
        pc = jitter(base_per_capita * PER_CAPITA_YEAR_FACTOR[year], 0.005)
        r = v * pc / 10000.0
        prov_annual[prov_name][year] = (round(v, 2), round(r, 2))

    years = sorted(YEAR_FACTOR.keys())
    for idx, year in enumerate(years):
        v, r = prov_annual[prov_name][year]
        per_capita = round(r * 10000.0 / v, 2)
        if idx == 0:
            yoy_v = yoy_r = None       # 首年无同比
        else:
            pv, pr = prov_annual[prov_name][years[idx - 1]]
            yoy_v = round((v - pv) / pv * 100, 2)
            yoy_r = round((r - pr) / pr * 100, 2)
        stats.append({
            'region': prov_name,
            'stat_type': 'annual',
            'year': year,
            'visitor_count': v,
            'revenue': r,
            'per_capita': per_capita,
            'yoy_visitor': yoy_v,
            'yoy_revenue': yoy_r,
            'data_source': DATA_SOURCE_HINT,
        })


# ============================================================
# 6. 生成节假日统计（2024 / 2025 × 国庆 / 春节 / 五一）
# ============================================================
for prov_name, _lng, _lat, _bv, _br, _cities in PROVINCES:
    for year in HOLIDAY_YEARS:
        year_v, year_r = prov_annual[prov_name][year]
        year_per_capita = year_r * 10000.0 / year_v

        for stat_type, v_ratio in HOLIDAY_VISITOR_RATIO.items():
            hv = round(jitter(year_v * v_ratio), 2)
            hp = round(jitter(year_per_capita * HOLIDAY_PER_CAPITA_RATIO[stat_type]), 2)
            hr = round(hv * hp / 10000.0, 2)

            # 同比：与该省上一年同假期口径比较（最早一年无同比）
            yoy_v = yoy_r = None
            if year > HOLIDAY_YEARS[0]:
                prev_v_annual, prev_r_annual = prov_annual[prov_name][year - 1]
                prev_v = prev_v_annual * v_ratio
                prev_r = prev_r_annual * HOLIDAY_PER_CAPITA_RATIO[stat_type] * v_ratio
                if prev_v and prev_r:
                    yoy_v = round((hv - prev_v) / prev_v * 100, 2)
                    yoy_r = round((hr - prev_r) / prev_r * 100, 2)

            stats.append({
                'region': prov_name,
                'stat_type': stat_type,
                'year': year,
                'visitor_count': hv,
                'revenue': hr,
                'per_capita': hp,
                'yoy_visitor': yoy_v,
                'yoy_revenue': yoy_r,
                'data_source': f'{DATA_SOURCE_HINT}｜{year}年{STAT_TYPE_CN[stat_type]}假期',
            })


# ============================================================
# 7. 生成城市榜单（3 个统计周期，各取前 10）
# ============================================================
CITY_RANKING_RAW = {
    '2024国庆': [
        ('成都市', 1450), ('西安市', 1320), ('长沙市', 1180), ('武汉市', 1150),
        ('广州市', 1120), ('杭州市', 1080), ('南京市', 1050), ('青岛市', 980),
        ('昆明市', 950), ('桂林市', 900),
    ],
    '2025国庆': [
        ('成都市', 1620), ('西安市', 1480), ('长沙市', 1330), ('武汉市', 1290),
        ('广州市', 1260), ('杭州市', 1210), ('南京市', 1180), ('厦门市', 1120),
        ('青岛市', 1090), ('张家界市', 1050),
    ],
    '2025五一': [
        ('成都市', 980), ('长沙市', 910), ('西安市', 880), ('杭州市', 850),
        ('武汉市', 820), ('南京市', 790), ('广州市', 770), ('苏州市', 750),
        ('青岛市', 720), ('厦门市', 700),
    ],
}

# 城市 -> 所属省份，用于取该省人均消费水平
city_to_prov = {}
for prov_name, _lng, _lat, _bv, _br, cities in PROVINCES:
    for c in cities:
        city_to_prov[c[0]] = prov_name

PERIOD_YEAR = {'2024国庆': 2024, '2025国庆': 2025, '2025五一': 2025}
PERIOD_TYPE = {'2024国庆': 'national_day', '2025国庆': 'national_day', '2025五一': 'labor_day'}

city_rankings = []
for period, rows in CITY_RANKING_RAW.items():
    year = PERIOD_YEAR[period]
    st = PERIOD_TYPE[period]
    for rank_no, (city_name, visitor) in enumerate(rows, start=1):
        prov = city_to_prov[city_name]
        year_v, year_r = prov_annual[prov][year]
        prov_per_capita = year_r * 10000.0 / year_v
        per_capita = round(jitter(prov_per_capita * HOLIDAY_PER_CAPITA_RATIO[st]), 2)
        visitor_f = round(jitter(visitor, 0.02), 2)
        revenue = round(visitor_f * per_capita / 10000.0, 2)
        city_rankings.append({
            'city': city_name,
            'period': period,
            'rank_no': rank_no,
            'visitor_count': visitor_f,
            'revenue': revenue,
            'per_capita': per_capita,
        })


# ============================================================
# 8. 汇总输出
# ============================================================
payload = {
    'note': '示例数据，仅用于系统演示',
    'disclaimer': (
        '本文件所有数值均按公开旅游统计公报的公开量级构造，并非真实采集结果，'
        '不得用于任何统计引用或对外发布。真实数据请运行 python manage.py crawl_tourism 采集。'
    ),
    'generated_at': '2026-09-24',
    'random_seed': SEED,
    'data_basis': {
        'year_factor_visitor': YEAR_FACTOR,
        'year_factor_per_capita': PER_CAPITA_YEAR_FACTOR,
        'holiday_visitor_ratio': HOLIDAY_VISITOR_RATIO,
        'holiday_per_capita_ratio': HOLIDAY_PER_CAPITA_RATIO,
        'calibration_note': (
            '【年度数据】2024 年各省基准值取自各省文旅厅/省政府公开口径的 2024 年度数据；'
            '2021—2023、2025 年按全国趋势系数外推（2022 年较 2021 年约 -22%，'
            '2023 年约 +93%，2024 年约 +15%，2024 年人均消费较 2023 年约 +2%，'
            '故收入增速快于客流增速）。'
        ),
        'holiday_note': (
            '【假期数据】为按比例估算值，非真实假期统计：'
            '以各省年度客流与人均消费为基数，乘以固定的假期比例系数得到。'
            '系数由 7 个省份 2024 年春节的官方数据反推，'
            '但各省假期特征差异较大（如广东因反向过年，春节客流占年度比重达 8.7%，'
            '远高于其他省份），统一系数无法逐省精确还原，'
            '故假期口径仅用于演示「节假日对比」图表功能，不可作为真实假期数据引用。'
        ),
    },
    'stat_type_legend': STAT_TYPE_CN,
    'counts': {
        'provinces': len(PROVINCES),
        'cities': sum(len(p[5]) for p in PROVINCES),
        'stats': len(stats),
        'city_rankings': len(city_rankings),
    },
    'regions': regions,
    'stats': stats,
    'city_rankings': city_rankings,
}

out_path = r'D:\ProjectFloder\tourism_project\backend\data\sample_data.json'
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print('已生成:', out_path)
print('统计:', payload['counts'])
print('文件大小: %.1f KB' % (os.path.getsize(out_path) / 1024))
