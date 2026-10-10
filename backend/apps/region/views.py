"""地区维度接口。

接口清单：
    GET /api/region/list/       地区列表（省份 / 城市），供前端下拉框使用
"""
from rest_framework.views import APIView

from apps.common.response import api_ok, api_fail, parse_int

from .models import Region
from .serializers import RegionListSerializer


class RegionListView(APIView):
    """地区列表接口。

    URL:    GET /api/region/list/
    参数:
        level   可选。1=省份，2=城市。不传则返回全部（省份在前）。
    返回:
        {"code":200,"msg":"success","data":[{"id":10,"name":"江苏省","level":1,"level_name":"省份"}, ...]}

    说明：前端「年度趋势」图表的省份选择器依赖本接口（level=1）。
    """

    def get(self, request):
        level, err = parse_int(request.query_params, 'level', min_value=1, max_value=2)
        if err:
            return api_fail(err)

        queryset = Region.objects.all()
        if level is not None:
            queryset = queryset.filter(level=level)
        queryset = queryset.order_by('level', 'id')

        data = RegionListSerializer(queryset, many=True).data
        return api_ok(data)
