"""旅游统计应用配置。"""
from django.apps import AppConfig


class TourismConfig(AppConfig):
    # 主键类型统一由 settings.DEFAULT_AUTO_FIELD 控制（不可在此覆盖）
    name = 'apps.tourism'
    label = 'tourism'
    verbose_name = '旅游统计'
