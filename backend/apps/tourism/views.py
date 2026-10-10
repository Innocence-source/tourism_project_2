"""
旅游统计接口（6 个业务接口 + 1 个元信息接口）
============================================

接口清单及约定：
    1. GET /api/tourism/map-heatmap/        地图热力      [{name, value}]
    2. GET /api/tourism/holiday-compare/    节假日对比    {省份: {各假期客流}}
    3. GET /api/tourism/city-ranking/       城市排名      [{name, visitor_count, revenue, per_capita}]
    4. GET /api/tourism/per-capita-scatter/ 人均消费散点  [{name, visitor, per_capita, revenue}]
    5. GET /api/tourism/yearly-trend/       年度趋势      [{year, visitor, revenue}]
    6. GET /api/tourism/summary/            大屏汇总      {total_visitor, total_revenue, top_province, avg_per_capita}
    7. GET /api/tourism/meta/               可选条件元信息（年份 / 周期 / 口径下拉框数据源）

统一返回体：{"code": 200, "msg": "success", "data": ...}

实现原则：
    - 全部使用 Django ORM 的 values / annotate / Sum / Avg，不写裸 SQL；
    - 所有 Decimal 一律转 float 后输出，避免前端 ECharts 拿到字符串；
    - 参数非法时返回 code=400 并给出中文原因，不抛 500。
"""
import re
from decimal import Decimal, InvalidOperation

from django.db.models import Sum, Avg
from rest_framework.views import APIView

from apps.common.response import api_ok, api_fail, parse_int, parse_str
from apps.region.models import Region

from .models import TourismStat, CityRanking
from .serializers import (
    MapHeatmapItemSerializer,
    HolidayCompareValueSerializer,
    CityRankingItemSerializer,
    PerCapitaScatterItemSerializer,
    YearlyTrendItemSerializer,
    SummarySerializer,
)

# ---------- 常量 ----------
STAT_TYPE_CHOICES = tuple(c[0] for c in TourismStat.STAT_TYPE_CHOICES)
STAT_TYPE_NAMES = dict(TourismStat.STAT_TYPE_CHOICES)
HOLIDAY_TYPES = (
    TourismStat.TYPE_NATIONAL,
    TourismStat.TYPE_SPRING,
    TourismStat.TYPE_LABOR,
)
METRIC_CHOICES = ('visitor_count', 'revenue')
METRIC_NAMES = {'visitor_count': '接待游客', 'revenue': '旅游收入'}
PROVINCE_LEVEL = Region.LEVEL_PROVINCE

# 数据口径提示语：由「示例数据」与「真实爬取数据」两种来源统一说明
CALIBER_LABEL = '样本省份合计'
CALIBER_NOTE = (
    '本系统当前仅入库部分省份数据，上述合计值为这些省份的加总，'
    '不代表全国总量。各省接待人次存在跨省重复统计，加总口径与全国口径不可直接等同。'
)


def _f(value):
    """Decimal / None -> float / None。

    ECharts 的数值轴只接受 number 类型；DRF 默认会把 Decimal 序列化成字符串，
    这里统一强制转换，避免图表静默不渲染。
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError, InvalidOperation):
        return None


# ---------- 统计周期排序（关键，勿简化）----------
# 假期在公历年内的时间顺序，用于正确判定「最新统计周期」。
# ⚠️ 不能直接对 period 字符串排序：中文按 Unicode 码点比较，
#    "2025春节"(春 U+6625) 会被排到 "2025国庆"(国 U+56FD) 之后，看似正确；
#    但换成 "2025五一"(五 U+4E94) 与 "2025国庆" 比较时结果同样反直觉。
#    统一走显式时序表，逻辑才可控。
HOLIDAY_SEQ = {'春节': 1, '五一': 2, '国庆': 3}


def _period_sort_key(period):
    """把 '2025国庆' 解析为 (2025, 3) 形式的可比较元组。"""
    match = re.match(r'^(\d{4})(.+)$', period or '')
    if not match:
        return (0, 0)
    year = int(match.group(1))
    name = match.group(2).strip()
    # 未登记的假期名归为 0，排在已登记假期之前
    return (year, HOLIDAY_SEQ.get(name, 0))


def _sorted_periods(desc=True):
    """返回库中全部统计周期，按「年份 + 假期时序」排序。

    注意：必须显式 order_by() 清空 CityRanking.Meta.ordering，
         否则 Django 会把 ordering 里的 rank_no 一并塞进 SELECT 子句，
         造成 DISTINCT 失效、同一周期被重复返回 N 次（N = 该周期的记录条数）。
    """
    periods = list(
        CityRanking.objects.order_by()
        .values_list('period', flat=True)
        .distinct()
    )
    return sorted(periods, key=_period_sort_key, reverse=desc)


def _parse_common(request):
    """解析各接口公共参数：year / stat_type。

    :return: (year, stat_type, error)
    """
    year, err = parse_int(request.query_params, 'year', default=2024,
                          min_value=2000, max_value=2100)
    if err:
        return None, None, err

    stat_type, err = parse_str(request.query_params, 'stat_type',
                               default=TourismStat.TYPE_ANNUAL, choices=STAT_TYPE_CHOICES)
    if err:
        return None, None, err

    return year, stat_type, None


# ============================================================
# 1. 地图热力
# ============================================================
class MapHeatmapView(APIView):
    """地图热力接口。

    URL:    GET /api/tourism/map-heatmap/
    参数:
        year       必填，默认 2024
        stat_type  可选，默认 annual（年度）
        metric     可选，visitor_count（客流，默认）/ revenue（收入）
    返回:
        [{"name": "河南省", "value": 95927.21}, ...]  按 value 降序

    说明：name 为行政区划全称，与前端 china.json 的 properties.name 完全一致，
         无需额外映射；未被数据库覆盖的省份不会出现在数组中，
         ECharts 的 visualMap 会将其渲染为无数据的默认色。
    """

    def get(self, request):
        year, stat_type, err = _parse_common(request)
        if err:
            return api_fail(err)

        metric, err = parse_str(request.query_params, 'metric',
                                default='visitor_count', choices=METRIC_CHOICES)
        if err:
            return api_fail(err)

        queryset = (
            TourismStat.objects
            .filter(stat_type=stat_type, year=year, region__level=PROVINCE_LEVEL)
            .values('region__name')
            .annotate(value=Sum(metric))
            .order_by('-value')
        )

        rows = [
            {'name': item['region__name'], 'value': _f(item['value'])}
            for item in queryset
        ]
        return api_ok(MapHeatmapItemSerializer(rows, many=True).data)


# ============================================================
# 2. 节假日对比
# ============================================================
class HolidayCompareView(APIView):
    """节假日对比接口。

    URL:    GET /api/tourism/holiday-compare/
    参数:
        year       必填，默认 2024
        metric     可选，visitor_count（默认）/ revenue
    返回:
        {"广东省": {"national_day": 5325.30, "spring_festival": 4514.65, "labor_day": 3201.20}, ...}

    说明：返回结构为「省份 -> 各假期指标」，字典序不保证稳定，
         前端展示建议先按 national_day 排序后再渲染。
    """

    def get(self, request):
        year, err = parse_int(request.query_params, 'year', default=2024,
                              min_value=2000, max_value=2100)
        if err:
            return api_fail(err)

        metric, err = parse_str(request.query_params, 'metric',
                                default='visitor_count', choices=METRIC_CHOICES)
        if err:
            return api_fail(err)

        queryset = (
            TourismStat.objects
            .filter(year=year, stat_type__in=HOLIDAY_TYPES, region__level=PROVINCE_LEVEL)
            .select_related('region')
        )

        # 先按省份聚合，再把缺失的口径补为 None，保证前端结构稳定
        bucket = {}
        for stat in queryset:
            row = bucket.setdefault(stat.region.name, {
                TourismStat.TYPE_NATIONAL: None,
                TourismStat.TYPE_SPRING: None,
                TourismStat.TYPE_LABOR: None,
            })
            row[stat.stat_type] = _f(getattr(stat, metric))

        data = {
            province: HolidayCompareValueSerializer(values).data
            for province, values in bucket.items()
        }
        return api_ok(data)


# ============================================================
# 3. 城市排名
# ============================================================
class CityRankingView(APIView):
    """城市排名接口。

    URL:    GET /api/tourism/city-ranking/
    参数:
        period  可选，如 2025国庆；不传则自动取库中最新周期
        limit   可选，默认 10，范围 1~50
    返回:
        [{"rank_no":1,"name":"成都市","visitor_count":1635.67,"revenue":188.90,"per_capita":1154.85}, ...]
    """

    def get(self, request):
        limit, err = parse_int(request.query_params, 'limit', default=10,
                               min_value=1, max_value=50)
        if err:
            return api_fail(err)

        period, err = parse_str(request.query_params, 'period')
        if err:
            return api_fail(err)

        queryset = CityRanking.objects.select_related('city')

        if period:
            if not CityRanking.objects.filter(period=period).exists():
                available = _sorted_periods(desc=True)
                return api_fail(
                    f'统计周期 {period} 无数据，可选值：'
                    f'{"、".join(available) or "（库中暂无榜单数据）"}',
                    code=404,
                )
            queryset = queryset.filter(period=period)
        else:
            # 未指定周期时自动取库中最新的一个，判定规则为「年份 + 假期时序」
            available = _sorted_periods(desc=True)
            if not available:
                return api_ok([])
            period = available[0]
            queryset = queryset.filter(period=period)

        queryset = queryset.order_by('rank_no', '-visitor_count')[:limit]

        rows = [
            {
                'rank_no': item.rank_no,
                'name': item.city.name,
                'visitor_count': _f(item.visitor_count),
                'revenue': _f(item.revenue),
                'per_capita': _f(item.per_capita),
            }
            for item in queryset
        ]
        return api_ok(CityRankingItemSerializer(rows, many=True).data)


# ============================================================
# 4. 人均消费散点
# ============================================================
class PerCapitaScatterView(APIView):
    """人均消费散点接口。

    URL:    GET /api/tourism/per-capita-scatter/
    参数:
        year       必填，默认 2024
        stat_type  可选，默认 annual
    返回:
        [{"name":"广东省","visitor":87176.21,"per_capita":1228.28,"revenue":10707.71}, ...]

    说明：X 轴客流、Y 轴人均消费、点大小按收入 —— 故必须同时返回 revenue，
         否则前端无法实现「点大小按收入」的视觉映射。
    """

    def get(self, request):
        year, stat_type, err = _parse_common(request)
        if err:
            return api_fail(err)

        queryset = (
            TourismStat.objects
            .filter(stat_type=stat_type, year=year, region__level=PROVINCE_LEVEL)
            .select_related('region')
            .order_by('-visitor_count')
        )

        rows = []
        for stat in queryset:
            # 散点图两个坐标轴缺一不可，任一为空则跳过该省份
            if stat.visitor_count is None or stat.per_capita is None:
                continue
            rows.append({
                'name': stat.region.name,
                'visitor': _f(stat.visitor_count),
                'per_capita': _f(stat.per_capita),
                'revenue': _f(stat.revenue),
            })

        return api_ok(PerCapitaScatterItemSerializer(rows, many=True).data)


# ============================================================
# 5. 年度趋势
# ============================================================
class YearlyTrendView(APIView):
    """年度趋势接口。

    URL:    GET /api/tourism/yearly-trend/
    参数:
        region_id  可选。不传时自动选用该口径下收入最高的省份
        stat_type  可选，默认 annual
    返回:
        [{"year":2021,"visitor":51769.25,"revenue":6999.77}, ...]  按年份升序
    """

    def get(self, request):
        stat_type, err = parse_str(request.query_params, 'stat_type',
                                   default=TourismStat.TYPE_ANNUAL,
                                   choices=STAT_TYPE_CHOICES)
        if err:
            return api_fail(err)

        region_id, err = parse_int(request.query_params, 'region_id', min_value=1)
        if err:
            return api_fail(err)

        region = None
        if region_id is not None:
            region = Region.objects.filter(pk=region_id).first()
            if region is None:
                return api_fail(f'地区 id={region_id} 不存在', code=404)
        else:
            # 未指定地区：默认展示收入最高的省份，保证前端首屏有数据
            top_stat = (
                TourismStat.objects
                .filter(stat_type=stat_type, region__level=PROVINCE_LEVEL, revenue__isnull=False)
                .select_related('region')
                .order_by('-revenue')
                .first()
            )
            region = top_stat.region if top_stat else Region.objects.filter(level=PROVINCE_LEVEL).first()

        if region is None:
            return api_ok([])

        queryset = (
            TourismStat.objects
            .filter(region=region, stat_type=stat_type)
            .order_by('year')
        )

        rows = [
            {
                'year': stat.year,
                'visitor': _f(stat.visitor_count),
                'revenue': _f(stat.revenue),
            }
            for stat in queryset
        ]
        return api_ok(YearlyTrendItemSerializer(rows, many=True).data)


# ============================================================
# 6. 大屏汇总
# ============================================================
class SummaryView(APIView):
    """大屏顶部指标卡汇总接口。

    URL:    GET /api/tourism/summary/
    参数:
        year       必填，默认 2024
        stat_type  可选，默认 annual
    返回:
        {
          "year": 2024, "stat_type": "annual",
          "total_visitor": 925868.65, "total_visitor_yi": 92.59,
          "total_revenue": 104142.71, "total_revenue_wanyi": 10.41,
          "top_province": {"id":17,"name":"江苏省","value":13000.00,
                           "metric":"revenue","metric_name":"旅游收入"},
          "avg_per_capita": 1124.78, "avg_per_capita_simple": 1115.31,
          "province_count": 12,
          "caliber": "样本省份合计",
          "note": "本系统当前仅入库部分省份数据，..."
        }

    口径设计（关键）：
        - total_visitor / total_revenue 为「参与统计的省份加总」，非全国总量，
          前端卡片必须标注 caliber 字段，不能写成「全国总客流」；
        - avg_per_capita 采用「总收入 ÷ 总客流」的加权实际人均，
          同时给出 avg_per_capita_simple（各省人均的算术平均）作为对照，
          避免答辩时被问「人均消费怎么算的」答不上来；
        - top_province 按**旅游收入**排序，对应大屏「收入第一省」指标卡。
    """

    def get(self, request):
        year, stat_type, err = _parse_common(request)
        if err:
            return api_fail(err)

        queryset = TourismStat.objects.filter(
            stat_type=stat_type, year=year, region__level=PROVINCE_LEVEL
        )

        agg = queryset.aggregate(
            total_visitor=Sum('visitor_count'),
            total_revenue=Sum('revenue'),
            avg_simple=Avg('per_capita'),
        )
        total_visitor = agg['total_visitor']
        total_revenue = agg['total_revenue']

        # 加权人均：总收入(亿元) × 1e8 ÷ 总客流(万人次) × 1e4
        avg_per_capita = None
        if total_visitor and total_revenue is not None:
            try:
                avg_per_capita = (
                    total_revenue * Decimal('10000') / total_visitor
                ).quantize(Decimal('0.01'))
            except (InvalidOperation, ZeroDivisionError):
                avg_per_capita = None

        # 换算值统一收敛小数位，避免前端拿到 92.586865 这类「脏精度」
        total_visitor_yi = (
            (total_visitor / Decimal('10000')).quantize(Decimal('0.01'))
            if total_visitor is not None else None
        )
        total_revenue_wanyi = (
            (total_revenue / Decimal('10000')).quantize(Decimal('0.0001'))
            if total_revenue is not None else None
        )
        avg_per_capita_simple = (
            agg['avg_simple'].quantize(Decimal('0.01'))
            if agg['avg_simple'] is not None else None
        )

        # 收入第一省
        top_stat = (
            queryset.filter(revenue__isnull=False)
            .select_related('region')
            .order_by('-revenue')
            .first()
        )
        top_province = None
        if top_stat:
            top_province = {
                'id': top_stat.region_id,
                'name': top_stat.region.name,
                'value': _f(top_stat.revenue),
                'metric': 'revenue',
                'metric_name': METRIC_NAMES['revenue'],
            }

        data = {
            'year': year,
            'stat_type': stat_type,
            'total_visitor': _f(total_visitor),
            'total_visitor_yi': _f(total_visitor_yi),
            'total_revenue': _f(total_revenue),
            'total_revenue_wanyi': _f(total_revenue_wanyi),
            'top_province': top_province,
            'avg_per_capita': _f(avg_per_capita),
            'avg_per_capita_simple': _f(avg_per_capita_simple),
            'province_count': queryset.count(),
            'caliber': CALIBER_LABEL,
            'note': CALIBER_NOTE,
        }
        return api_ok(SummarySerializer(data).data)


# ============================================================
# 7. 元信息（前端下拉框数据源）
# ============================================================
class MetaView(APIView):
    """系统可选条件元信息接口。

    URL:    GET /api/tourism/meta/
    返回:
        {
          "years": [2025, 2024, 2023, 2022, 2021],
          "periods": ["2025国庆", "2025五一", "2024国庆"],
          "stat_types": [{"value":"annual","label":"年度"}, ...],
          "provinces": [{"id":1,"name":"广东省"}, ...],
          "default_year": 2025,
          "default_period": "2025国庆"
        }

    说明：本接口不在原始需求的 7 个接口之内，是为解决
         「前端年份 / 周期选择器从哪里取候选值」而补充的，
         否则下拉框只能硬编码，年份切换功能会与数据库脱节。
    """

    def get(self, request):
        years = list(
            TourismStat.objects.values_list('year', flat=True)
            .distinct().order_by('-year')
        )
        periods = _sorted_periods(desc=True)
        provinces = list(
            Region.objects.filter(level=PROVINCE_LEVEL)
            .values('id', 'name').order_by('id')
        )

        data = {
            'years': years,
            'periods': periods,
            'stat_types': [
                {'value': value, 'label': label}
                for value, label in TourismStat.STAT_TYPE_CHOICES
            ],
            'provinces': provinces,
            'default_year': years[0] if years else None,
            'default_period': periods[0] if periods else None,
            'data_note': '库内数据来源见 crawl_log，示例数据已在 data_source 字段标注',
        }
        return api_ok(data)
