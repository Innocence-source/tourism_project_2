"""
MySQL 精确类型字段
==================

Django 的字段类型与 MySQL 类型并非一一对应，默认映射会与数据库设计文档产生偏差：

    Django 字段            默认生成的 MySQL 类型    设计文档要求    差异
    -------------------    --------------------    -----------    ----
    BigAutoField           bigint                  int            ✗
    SmallIntegerField      smallint                tinyint        ✗
    TextField              longtext                text           ✗
    DateTimeField          datetime(6)             datetime       ✗（多出微秒精度）

本模块提供薄封装字段，把上述差异对齐到设计文档。
所有字段均按 connection.vendor 判断，非 MySQL 环境自动回退 Django 默认行为，
保证换库（如 SQLite 做单元测试）时不会报错。

⚠️ 注意：DATETIME 的 `DEFAULT CURRENT_TIMESTAMP` 无法通过字段声明表达
   （Django 的 db_type() 不接受默认值），因此在迁移中使用 RunSQL 单独 ALTER。
   见 apps/*/migrations/0002_*.py
"""
from django.db import models


class TinyIntegerField(models.SmallIntegerField):
    """MySQL TINYINT（1 字节）。用于取值有限的枚举型数字，如 region.level。"""

    def db_type(self, connection):
        if connection.vendor == 'mysql':
            return 'tinyint'
        return super().db_type(connection)


class MySQLTextField(models.TextField):
    """MySQL TEXT（64KB）。

    Django 的 TextField 默认生成 longtext（4GB）。对于短日志文本（crawl_log.message），
    用 longtext 属于类型过宽，与设计文档不符。
    """

    def db_type(self, connection):
        if connection.vendor == 'mysql':
            return 'text'
        return super().db_type(connection)


class SecondDateTimeField(models.DateTimeField):
    """秒精度 DATETIME（不含微秒）。

    Django 的 DateTimeField 默认生成 datetime(6)。本系统的入库时间 / 采集时间
    只用于展示与排序，秒级精度足够，多余的 6 位小数会与设计文档不符。
    """

    def db_type(self, connection):
        if connection.vendor == 'mysql':
            return 'datetime'
        return super().db_type(connection)
