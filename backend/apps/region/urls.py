"""地区维度路由。

由 tourism_project/urls.py 以 path('api/region/', include(...)) 挂载，
故本文件内路径不含 api/region 前缀。
"""
from django.urls import path

from .views import RegionListView

app_name = 'region'

urlpatterns = [
    # GET /api/region/list/
    path('list/', RegionListView.as_view(), name='region-list'),
]
