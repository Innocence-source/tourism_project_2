"""
旅游统计模型

对应数据库表：
    tourism_stat  —— 旅游统计主表（年度 + 节假日）
    city_ranking  —— 城市榜单表
    crawl_log     —— 爬虫运行日志表

设计要点：
    1. 三个表同属「旅游统计」业务域，故统一放在 tourism 应用中，
       避免为 crawl_log 单独新增 crawler/models.py 而偏离既定目录结构；
    2. 金额统一使用 DecimalField，杜绝浮点误差，DB 侧为 DECIMAL；
    3. (region, stat_type, year) 唯一约束，是爬虫 update_or_create 幂等入库的基础。
"""
from django.db import models

from apps.common.fields import MySQLTextField, SecondDateTimeField


class TourismStat(models.Model):
    """旅游统计数据（某地区某年某口径的客流 / 收入 / 人均消费）"""

    # 本表主键按设计文档要求为 BIGINT，需显式声明；
    # 其余三张表的主键由 settings.DEFAULT_AUTO_FIELD 统一生成 int
    id = models.BigAutoField(primary_key=True)

    # ---------- 统计口径 ----------
    TYPE_ANNUAL = 'annual'                  # 年度汇总
    TYPE_SPRING = 'spring_festival'         # 春节假期
    TYPE_NATIONAL = 'national_day'          # 国庆假期
    TYPE_LABOR = 'labor_day'                # 五一假期
    STAT_TYPE_CHOICES = (
        (TYPE_ANNUAL, '年度'),
        (TYPE_SPRING, '春节'),
        (TYPE_NATIONAL, '国庆'),
        (TYPE_LABOR, '五一'),
    )

    region = models.ForeignKey(
        'region.Region',
        verbose_name='地区',
        on_delete=models.CASCADE,
        related_name='stats',
        help_text='省份或城市',
    )
    stat_type = models.CharField(
        '统计口径', max_length=20, choices=STAT_TYPE_CHOICES, default=TYPE_ANNUAL
    )
    year = models.IntegerField('年份')

    visitor_count = models.DecimalField(
        '接待游客', max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='单位：万人次',
    )
    revenue = models.DecimalField(
        '旅游收入', max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='单位：亿元',
    )
    per_capita = models.DecimalField(
        '人均消费', max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='单位：元。由 收入 ÷ 客流 换算后落库，便于直接排序展示',
    )

    # 同比增速，单位 %。首年数据无同比，允许为空
    yoy_visitor = models.DecimalField(
        '客流同比', max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='单位：%',
    )
    yoy_revenue = models.DecimalField(
        '收入同比', max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='单位：%',
    )

    data_source = models.CharField(
        '数据来源', max_length=100, blank=True, default='',
        help_text='如「广东省文化和旅游厅 2024 年国庆假期旅游统计公报」',
    )
    # 秒精度 DATETIME；DEFAULT CURRENT_TIMESTAMP 由迁移 0002 用 RunSQL 补上
    created_at = SecondDateTimeField('入库时间', auto_now_add=True)

    class Meta:
        db_table = 'tourism_stat'
        verbose_name = '旅游统计'
        verbose_name_plural = '旅游统计'
        # 唯一约束：同一地区 + 同一口径 + 同一年份 只允许一条记录
        # 这是爬虫 update_or_create 幂等性的前提
        constraints = [
            models.UniqueConstraint(
                fields=['region', 'stat_type', 'year'],
                name='uk_region_type_year',
            ),
        ]
        indexes = [
            models.Index(fields=['year'], name='idx_year'),
            models.Index(fields=['stat_type'], name='idx_type'),
            # 大屏最常用组合：按年份 + 口径筛选
            models.Index(fields=['year', 'stat_type'], name='idx_year_type'),
        ]
        ordering = ['-year', 'region_id']

    def __str__(self):
        return f'{self.region.name}-{self.get_stat_type_display()}-{self.year}'

    # ---------- 计算属性：供序列化器 / 管理后台直接使用 ----------
    @property
    def visitor_count_yi(self):
        """客流量换算为「亿人次」，用于大屏顶部总客流展示"""
        if self.visitor_count is None:
            return None
        return float(self.visitor_count) / 10000

    @staticmethod
    def calc_per_capita(visitor_count, revenue):
        """人均消费 = 旅游收入(亿元) × 1e8 ÷ 客流(万人次) × 1e4，结果单位为元。

        :param visitor_count: 接待游客，单位万人次
        :param revenue: 旅游收入，单位亿元
        :return: 人均消费（元），参数缺失或客流为 0 时返回 None
        """
        if not visitor_count or revenue is None:
            return None
        try:
            vc = float(visitor_count)
            rv = float(revenue)
        except (TypeError, ValueError):
            return None
        if vc == 0:
            return None
        # 约分后：revenue * 10000 / visitor_count
        return round(rv * 10000.0 / vc, 2)


class CityRanking(models.Model):
    """城市榜单（某统计周期的城市客流 / 收入排名）"""

    city = models.ForeignKey(
        'region.Region',
        verbose_name='城市',
        on_delete=models.CASCADE,
        related_name='rankings',
        db_column='city_id',
        # 后台下拉框只允许选择「城市」层级的记录，避免误选省份
        limit_choices_to={'level': 2},
    )
    period = models.CharField(
        '统计周期', max_length=30,
        help_text='如「2025五一」「2025国庆」',
    )
    rank_no = models.IntegerField('排名', null=True, blank=True)
    visitor_count = models.DecimalField(
        '接待游客', max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='单位：万人次',
    )
    revenue = models.DecimalField(
        '旅游收入', max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='单位：亿元',
    )
    per_capita = models.DecimalField(
        '人均消费', max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='单位：元',
    )

    class Meta:
        db_table = 'city_ranking'
        verbose_name = '城市榜单'
        verbose_name_plural = '城市榜单'
        constraints = [
            models.UniqueConstraint(
                fields=['city', 'period'], name='uk_city_period'
            ),
        ]
        indexes = [
            models.Index(fields=['period'], name='idx_period'),
        ]
        ordering = ['period', 'rank_no']

    def __str__(self):
        return f'{self.period}-{self.city.name}'


class CrawlLog(models.Model):
    """爬虫运行日志（每次采集写入一条，便于追溯数据来源）"""

    STATUS_CHOICES = (
        ('success', '成功'),
        ('failed', '失败'),
        ('partial', '部分成功'),
    )

    source = models.CharField('数据源', max_length=100, blank=True, default='')
    status = models.CharField(
        '状态', max_length=20, choices=STATUS_CHOICES, blank=True, default='success'
    )
    # 短日志文本用 MySQL TEXT 即可，Django 默认的 longtext 过宽
    message = MySQLTextField('详细信息', blank=True, default='')
    # 秒精度 DATETIME；DEFAULT CURRENT_TIMESTAMP 由迁移 0002 用 RunSQL 补上
    crawled_at = SecondDateTimeField('采集时间', auto_now_add=True)

    class Meta:
        db_table = 'crawl_log'
        verbose_name = '爬虫日志'
        verbose_name_plural = '爬虫日志'
        ordering = ['-crawled_at']

    def __str__(self):
        return f'[{self.crawled_at:%Y-%m-%d %H:%M:%S}] {self.source} - {self.status}'
