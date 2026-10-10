"""地区维度后台管理配置。"""
from django.contrib import admin

from .models import Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    """省份 / 城市数据的后台管理"""

    # 列表展示字段
    list_display = ('id', 'name', 'level_display', 'parent', 'longitude', 'latitude')
    # 右侧过滤器
    list_filter = ('level',)
    # 顶部搜索
    search_fields = ('name',)
    # 排序
    ordering = ('level', 'id')
    # 每页条数
    list_per_page = 50
    # 关联查询优化，避免 N+1
    list_select_related = ('parent',)

    @admin.display(description='层级', ordering='level')
    def level_display(self, obj):
        """把 level 数字渲染为中文标签"""
        return obj.get_level_display()
