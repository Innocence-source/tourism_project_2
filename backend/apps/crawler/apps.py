"""爬虫应用配置。

本应用无 models.py —— 爬虫日志复用 tourism.CrawlLog，
以保持目录结构与设计文档完全一致。
"""
from django.apps import AppConfig


class CrawlerConfig(AppConfig):
    # 主键类型统一由 settings.DEFAULT_AUTO_FIELD 控制（不可在此覆盖）
    name = 'apps.crawler'
    label = 'crawler'
    verbose_name = '数据采集'
