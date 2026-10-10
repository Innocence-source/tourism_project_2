"""地区应用配置。"""
from django.apps import AppConfig


class RegionConfig(AppConfig):
    # 主键类型统一由 settings.DEFAULT_AUTO_FIELD 控制
    # （此处不可再写 default_auto_field，否则会覆盖全局配置，
    #   导致主键生成 bigint 而非设计文档要求的 int）
    name = 'apps.region'
    # label 决定数据库表默认前缀与 admin 中的应用名，显式指定更直观
    label = 'region'
    verbose_name = '地区维度'
