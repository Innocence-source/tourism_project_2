"""
数据分析接口（增值扩展）
========================

本应用定位：在 tourism 应用提供的「基础看板接口」之上，
提供需要跨口径计算的**深度分析接口**。

接口清单：
    GET /api/analysis/growth-ranking/    同比增速排行

说明：原始需求中未包含本组接口，此处为让 analysis 应用具备实质分析能力而补充，
     属于 7 个必做接口之外的加分项，可安全删除而不影响主流程。
"""
from decimal import InvalidOperation

from django.db.models import Avg
from rest_framework.views import APIView

from apps.common.response import api_ok, api_fail, parse_int, parse_str
from apps.region.models import Region
from apps.tourism.models import TourismStat


def _f(value):
    """Decimal / None -> float / None"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError, InvalidOperation):
        return None


class GrowthRankingView(APIView):
    """同比增速排行接口。

    URL:    GET /api/analysis/growth-ranking/
    参数:
        year       必填，默认 2024
        stat_type  可选，默认 annual
        metric     可选，yoy_revenue（收入增速，默认）/ yoy_visitor（客流增速）
        order      可选，desc（降序，默认）/ asc（升序）
        limit      可选，默认 10，范围 1~50
    返回:
        {"metric":"yoy_revenue","metric_name":"收入同比",
         "items":[{"rank":1,"name":"江苏省","yoy_revenue":15.2,"yoy_visitor":17.7,
                   "visitor_count":91508.86,"revenue":12755.12}, ...],
         "avg_yoy": 14.83}

    用途：识别增长最快的省份，可作为大屏「增长之星」模块，
         也是「数据分析」这一毕设命题的直观体现。
    """

    METRIC_NAMES = {
        'yoy_revenue': '收入同比',
        'yoy_visitor': '客流同比',
    }

    def get(self, request):
        year, err = parse_int(request.query_params, 'year', default=2024,
                              min_value=2000, max_value=2100)
        if err:
            return api_fail(err)

        stat_type, err = parse_str(request.query_params, 'stat_type',
                                   default=TourismStat.TYPE_ANNUAL,
                                   choices=tuple(c[0] for c in TourismStat.STAT_TYPE_CHOICES))
        if err:
            return api_fail(err)

        metric, err = parse_str(request.query_params, 'metric',
                                default='yoy_revenue', choices=tuple(self.METRIC_NAMES.keys()))
        if err:
            return api_fail(err)

        order, err = parse_str(request.query_params, 'order',
                               default='desc', choices=('desc', 'asc'))
        if err:
            return api_fail(err)

        limit, err = parse_int(request.query_params, 'limit', default=10,
                               min_value=1, max_value=50)
        if err:
            return api_fail(err)

        queryset = TourismStat.objects.filter(
            stat_type=stat_type,
            year=year,
            region__level=Region.LEVEL_PROVINCE,
            **{f'{metric}__isnull': False},        # 首年无同比，必须排除
        ).select_related('region')

        # 排序方向
        queryset = queryset.order_by(f'-{metric}' if order == 'desc' else metric)[:limit]

        items = []
        for idx, stat in enumerate(queryset, start=1):
            items.append({
                'rank': idx,
                'name': stat.region.name,
                'yoy_revenue': _f(stat.yoy_revenue),
                'yoy_visitor': _f(stat.yoy_visitor),
                'visitor_count': _f(stat.visitor_count),
                'revenue': _f(stat.revenue),
            })

        # 全样本平均增速（同口径、排除空值）
        avg_value = (
            TourismStat.objects
            .filter(stat_type=stat_type, year=year,
                    region__level=Region.LEVEL_PROVINCE,
                    **{f'{metric}__isnull': False})
            .aggregate(v=Avg(metric))['v']
        )

        return api_ok({
            'year': year,
            'stat_type': stat_type,
            'metric': metric,
            'metric_name': self.METRIC_NAMES[metric],
            'order': order,
            'items': items,
            'avg_yoy': _f(avg_value),
        })
