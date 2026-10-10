"""分析应用配置。"""
from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    # 主键类型统一由 settings.DEFAULT_AUTO_FIELD 控制（不可在此覆盖）
    name = 'apps.analysis'
    label = 'analysis'
    verbose_name = '数据分析'
