"""旅游统计序列化器。

统一约定（重要）：
    所有数值字段一律使用 FloatField 而非 DecimalField。
    原因：DRF 默认把 Decimal 序列化为**字符串**（如 "5325.30"），
          ECharts 收到字符串后无法参与数值轴映射，图表会静默渲染失败。
          这里显式转 float，保证前端拿到的是数字类型。
"""
from rest_framework import serializers

from .models import TourismStat, CityRanking


# ============================================================
# 1. 地图热力
# ============================================================
class MapHeatmapItemSerializer(serializers.Serializer):
    """地图热力数据项。

    注意：name 必须与前端 china.json 中 Feature.properties.name 完全一致。
    本系统 GeoJSON 采用行政区划全称（如「广东省」「广西壮族自治区」），
    数据库存储的也是全称，二者天然匹配，无需映射表。
    """

    name = serializers.CharField()
    value = serializers.FloatField(allow_null=True)


# ============================================================
# 2. 节假日对比
# ============================================================
class HolidayCompareValueSerializer(serializers.Serializer):
    """单个省份在各类假期下的客流（万人次）。缺少该口径数据时为 None。"""

    national_day = serializers.FloatField(allow_null=True)
    spring_festival = serializers.FloatField(allow_null=True)
    labor_day = serializers.FloatField(allow_null=True)


# ============================================================
# 3. 城市排名
# ============================================================
class CityRankingItemSerializer(serializers.Serializer):
    """城市榜单数据项，字段名遵循前端 ECharts 直接消费的习惯。"""

    rank_no = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    visitor_count = serializers.FloatField(allow_null=True)
    revenue = serializers.FloatField(allow_null=True)
    per_capita = serializers.FloatField(allow_null=True)


# ============================================================
# 4. 人均消费散点
# ============================================================
class PerCapitaScatterItemSerializer(serializers.Serializer):
    """散点图数据项。

    字段说明：
        visitor      X 轴 —— 接待游客（万人次）
        per_capita   Y 轴 —— 人均消费（元）
        revenue      气泡大小 —— 旅游收入（亿元）

    注：原始需求中的返回示例为 [{name, visitor, per_capita}]，
        缺少 revenue 会导致「点大小按收入」这一图表需求无法实现，
        故此处显式补上 revenue 字段。
    """

    name = serializers.CharField()
    visitor = serializers.FloatField(allow_null=True)
    per_capita = serializers.FloatField(allow_null=True)
    revenue = serializers.FloatField(allow_null=True)


# ============================================================
# 5. 年度趋势
# ============================================================
class YearlyTrendItemSerializer(serializers.Serializer):
    """年度趋势数据项，按年份升序。"""

    year = serializers.IntegerField()
    visitor = serializers.FloatField(allow_null=True)
    revenue = serializers.FloatField(allow_null=True)


# ============================================================
# 6. 大屏汇总
# ============================================================
class TopProvinceSerializer(serializers.Serializer):
    """「收入第一省」信息。"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    value = serializers.FloatField(allow_null=True)      # 该省收入（亿元）
    metric = serializers.CharField()                     # 排序依据字段名
    metric_name = serializers.CharField()                # 排序依据中文名


class SummarySerializer(serializers.Serializer):
    """大屏顶部指标卡数据。

    ⚠️ 口径说明（必须理解，否则答辩会被质疑）：
        本系统当前仅入库部分省份数据，total_visitor / total_revenue 是
        **这些省份的合计值，不是全国总量**。因此额外返回 caliber 与 note 字段，
        前端必须在卡片上标注口径，不能直接写「全国总客流」。
    """

    year = serializers.IntegerField()
    stat_type = serializers.CharField()

    total_visitor = serializers.FloatField(allow_null=True)       # 单位：万人次
    total_visitor_yi = serializers.FloatField(allow_null=True)    # 单位：亿人次（已换算，便于大屏直接展示）
    total_revenue = serializers.FloatField(allow_null=True)       # 单位：亿元
    total_revenue_wanyi = serializers.FloatField(allow_null=True)  # 单位：万亿元（已换算）

    top_province = TopProvinceSerializer(allow_null=True)

    # 人均消费 = 总收入 / 总客流，属于「加权实际人均」，
    # 比「各省人均消费的算术平均」更符合真实口径
    avg_per_capita = serializers.FloatField(allow_null=True)      # 单位：元
    avg_per_capita_simple = serializers.FloatField(allow_null=True)  # 各省人均的算术平均（对照用）

    province_count = serializers.IntegerField()                   # 参与统计的省份数量
    caliber = serializers.CharField()                             # 口径标签
    note = serializers.CharField()                                # 口径补充说明


# ============================================================
# 7. 通用：模型序列化器（供扩展与调试使用）
# ============================================================
class TourismStatSerializer(serializers.ModelSerializer):
    """旅游统计明细，供后续数据导出 / 明细查询扩展。"""

    region_name = serializers.CharField(source='region.name', read_only=True)
    stat_type_name = serializers.SerializerMethodField()

    class Meta:
        model = TourismStat
        fields = ('id', 'region', 'region_name', 'stat_type', 'stat_type_name',
                  'year', 'visitor_count', 'revenue', 'per_capita',
                  'yoy_visitor', 'yoy_revenue', 'data_source', 'created_at')

    def get_stat_type_name(self, obj):
        return obj.get_stat_type_display()


class CityRankingSerializer(serializers.ModelSerializer):
    """城市榜单明细。"""

    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = CityRanking
        fields = ('id', 'city', 'city_name', 'period', 'rank_no',
                  'visitor_count', 'revenue', 'per_capita')
