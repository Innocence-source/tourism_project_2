"""旅游统计路由。

由 tourism_project/urls.py 以 path('api/tourism/', include(...)) 挂载，
故本文件内路径不含 api/tourism 前缀。
"""
from django.urls import path

from .views import (
    MapHeatmapView,
    HolidayCompareView,
    CityRankingView,
    PerCapitaScatterView,
    YearlyTrendView,
    SummaryView,
    MetaView,
)

app_name = 'tourism'

urlpatterns = [
    # 1. 地图热力        /api/tourism/map-heatmap/?year=2024&stat_type=annual
    path('map-heatmap/', MapHeatmapView.as_view(), name='map-heatmap'),

    # 2. 节假日对比      /api/tourism/holiday-compare/?year=2024
    path('holiday-compare/', HolidayCompareView.as_view(), name='holiday-compare'),

    # 3. 城市排名        /api/tourism/city-ranking/?period=2025国庆&limit=10
    path('city-ranking/', CityRankingView.as_view(), name='city-ranking'),

    # 4. 人均消费散点    /api/tourism/per-capita-scatter/?year=2024&stat_type=annual
    path('per-capita-scatter/', PerCapitaScatterView.as_view(), name='per-capita-scatter'),

    # 5. 年度趋势        /api/tourism/yearly-trend/?region_id=10
    path('yearly-trend/', YearlyTrendView.as_view(), name='yearly-trend'),

    # 6. 大屏汇总        /api/tourism/summary/?year=2024
    path('summary/', SummaryView.as_view(), name='summary'),

    # 7. 元信息（补充接口） /api/tourism/meta/
    path('meta/', MetaView.as_view(), name='meta'),
]
