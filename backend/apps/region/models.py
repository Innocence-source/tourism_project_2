"""
地区维度模型

对应数据库表：
    region(id, name, parent_id, level, longitude, latitude)
设计要点：
    1. 省份与城市共用一张表，通过 level 区分（1=省份，2=城市）；
    2. parent 为自关联外键，城市指向其所属省份，比裸 parent_id 更利于 ORM 聚合；
    3. 经纬度保留，供前端地图散点 / 定位扩展使用。
"""
from django.db import models

from apps.common.fields import TinyIntegerField


class Region(models.Model):
    """行政区划（省份 / 城市）"""

    # ---------- 层级常量：便于代码中写成 Region.LEVEL_PROVINCE，避免魔法数字 ----------
    LEVEL_PROVINCE = 1
    LEVEL_CITY = 2
    LEVEL_CHOICES = (
        (LEVEL_PROVINCE, '省份'),
        (LEVEL_CITY, '城市'),
    )

    name = models.CharField('地区名称', max_length=50)

    # 自关联外键：省份的 parent 为空，城市的 parent 指向所属省份
    # db_column='parent_id' 保证实际字段名与设计文档一致
    parent = models.ForeignKey(
        'self',
        verbose_name='上级地区',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        db_column='parent_id',
    )

    # 用 TinyIntegerField 生成 MySQL TINYINT，与设计文档严格一致
    # （Django 原生 SmallIntegerField 会生成 smallint）
    level = TinyIntegerField(
        '层级',
        choices=LEVEL_CHOICES,
        default=LEVEL_PROVINCE,
        help_text='1=省份，2=城市',
    )

    longitude = models.DecimalField(
        '经度', max_digits=10, decimal_places=6, null=True, blank=True
    )
    latitude = models.DecimalField(
        '纬度', max_digits=10, decimal_places=6, null=True, blank=True
    )

    class Meta:
        db_table = 'region'                       # 表名与设计文档保持一致
        verbose_name = '地区'
        verbose_name_plural = '地区'
        # 同一层级下不允许重名
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'level'], name='uk_name_level'
            ),
        ]
        indexes = [
            models.Index(fields=['level'], name='idx_level'),          # 按层级筛选
            models.Index(fields=['parent'], name='idx_region_parent'),  # 按省份查城市
        ]
        ordering = ['level', 'id']

    def __str__(self):
        """Admin 及 shell 中显示为「广东省 / 广州市」"""
        return self.name
