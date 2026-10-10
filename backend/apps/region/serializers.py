"""地区维度序列化器。

作用：把 Region 模型对象固化为前端约定的输出契约，
      避免视图里手写 dict 导致字段名漂移。
"""
from rest_framework import serializers

from .models import Region


class RegionListSerializer(serializers.ModelSerializer):
    """地区列表项 —— 用于前端下拉选择器。

    输出：{"id": 1, "name": "广东省", "level": 1}
    level 供前端区分省份 / 城市，忽略亦不影响使用。
    """

    level_name = serializers.CharField(source='get_level_display', read_only=True)

    class Meta:
        model = Region
        fields = ('id', 'name', 'level', 'level_name')


class RegionDetailSerializer(serializers.ModelSerializer):
    """地区详情 —— 含上级地区与经纬度，供扩展使用。"""

    parent_name = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ('id', 'name', 'level', 'parent', 'parent_name',
                  'longitude', 'latitude')

    def get_parent_name(self, obj):
        """上级地区名称，省份无上级时返回 None。"""
        return obj.parent.name if obj.parent_id else None
