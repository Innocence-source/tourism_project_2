"""旅游统计后台管理配置。

Django Admin 是本系统的「数据管理」模块，需支持查看与编辑：
    - 旅游统计（含按年份 / 口径筛选、客流收入排序）
    - 城市榜单
    - 爬虫日志（只读，防止人工篡改留痕）
"""
from django.contrib import admin

from .models import TourismStat, CityRanking, CrawlLog


@admin.register(TourismStat)
class TourismStatAdmin(admin.ModelAdmin):
    """旅游统计数据管理"""

    list_display = (
        'id', 'region', 'stat_type_display', 'year',
        'visitor_count', 'revenue', 'per_capita',
        'yoy_visitor', 'yoy_revenue', 'data_source',
    )
    list_filter = ('stat_type', 'year', 'region__level')
    search_fields = ('region__name', 'data_source')
    ordering = ('-year', 'region_id')
    list_per_page = 50
    # 关联预取，避免列表页 N+1 查询
    list_select_related = ('region',)

    # 表单中人均消费可留空，由保存时自动换算
    fieldsets = (
        ('基础信息', {
            'fields': ('region', 'stat_type', 'year', 'data_source'),
        }),
        ('核心指标', {
            'fields': ('visitor_count', 'revenue', 'per_capita'),
            'description': '客流量单位万人次，收入单位亿元，人均消费单位元。'
                           '人均消费留空时会根据收入与客流自动换算。',
        }),
        ('同比增速', {
            'fields': ('yoy_visitor', 'yoy_revenue'),
        }),
    )
    readonly_fields = ()

    @admin.display(description='统计口径', ordering='stat_type')
    def stat_type_display(self, obj):
        return obj.get_stat_type_display()

    def save_model(self, request, obj, form, change):
        """保存前若人均消费为空，自动按 收入/客流 换算补齐。"""
        if obj.per_capita is None:
            obj.per_capita = TourismStat.calc_per_capita(
                obj.visitor_count, obj.revenue
            )
        super().save_model(request, obj, form, change)


@admin.register(CityRanking)
class CityRankingAdmin(admin.ModelAdmin):
    """城市榜单管理"""

    list_display = (
        'id', 'period', 'rank_no', 'city',
        'visitor_count', 'revenue', 'per_capita',
    )
    list_filter = ('period',)
    search_fields = ('city__name',)
    ordering = ('period', 'rank_no')
    list_per_page = 50
    list_select_related = ('city',)


@admin.register(CrawlLog)
class CrawlLogAdmin(admin.ModelAdmin):
    """爬虫日志：只读，保证采集痕迹不可被人为修改"""

    list_display = ('id', 'source', 'status', 'short_message', 'crawled_at')
    list_filter = ('status', 'source')
    search_fields = ('source', 'message')
    ordering = ('-crawled_at',)
    list_per_page = 50

    @admin.display(description='详细信息')
    def short_message(self, obj):
        """列表页截断过长消息"""
        if not obj.message:
            return '-'
        return obj.message[:60] + ('...' if len(obj.message) > 60 else '')

    # ---------- 只读控制 ----------
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True
