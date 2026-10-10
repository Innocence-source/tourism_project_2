"""数据分析路由。

由 tourism_project/urls.py 以 path('api/analysis/', include(...)) 挂载。
"""
from django.urls import path

from .views import GrowthRankingView

app_name = 'analysis'

urlpatterns = [
    # GET /api/analysis/growth-ranking/?year=2024&metric=yoy_revenue&limit=10
    path('growth-ranking/', GrowthRankingView.as_view(), name='growth-ranking'),
]
