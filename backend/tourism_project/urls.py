"""
URL 总路由

第三阶段已完成，现挂载：
    /admin/          Django Admin 数据管理后台
    /api/region/     地区维度接口（地区列表）
    /api/tourism/    旅游统计看板接口（6 个业务接口 + 1 个元信息接口）
    /api/analysis/   深度分析接口（同比增速排行）
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # 后台数据管理入口：http://127.0.0.1:8001/admin/
    path('admin/', admin.site.urls),
]

# ---------- 业务接口路由 ----------
urlpatterns += [
    # 地区维度：地区列表（前端省份 / 城市下拉框数据源）
    path('api/region/', include('apps.region.urls')),

    # 旅游统计：地图热力 / 节假日对比 / 城市排名 / 人均消费散点 /
    #           年度趋势 / 大屏汇总 / 元信息
    path('api/tourism/', include('apps.tourism.urls')),

    # 深度分析：同比增速排行
    path('api/analysis/', include('apps.analysis.urls')),
]

# 后台站点标题（中文）
admin.site.site_header = '全国旅游数据分析与可视化系统 · 后台管理'
admin.site.site_title = '旅游数据管理'
admin.site.index_title = '数据管理'
