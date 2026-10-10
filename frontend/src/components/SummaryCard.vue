<template>
    <div class="summary-row">
        <div
            v-for="card in cards"
            :key="card.key"
            class="summary-card"
            :class="{ 'is-error': !!errorMsg }"
        >
            <div class="card-label">
                {{ card.label }}
                <!-- 口径标签：提醒「样本省份合计」而非全国总量 -->
                <span v-if="card.caliber" class="card-caliber">{{ card.caliber }}</span>
            </div>

            <div class="card-value">
                <span class="card-number">{{ card.value }}</span>
                <span v-if="card.unit" class="card-unit">{{ card.unit }}</span>
            </div>

            <div class="card-extra">{{ errorMsg || card.extra }}</div>
        </div>
    </div>
</template>

<script setup>
/**
 * 关键指标卡片组件
 * ================
 * 大屏顶部的 4 张数字卡片：总客流 / 总收入 / 收入第一省 / 人均消费。
 *
 * 数据来源：GET /api/tourism/summary/
 *
 * ⚠️ 口径说明（重要，答辩必问）：
 *    后端返回的 total_visitor / total_revenue 是**参与统计的省份加总**，
 *    不是全国总量（各省接待人次存在跨省重复统计）。
 *    因此卡片上必须展示后端返回的 caliber 字段（「样本省份合计」），
 *    绝不能写成「全国总客流」。
 *
 * 人均消费同样有两个口径：
 *    avg_per_capita         加权实际人均（总收入 ÷ 总客流）—— 主展示
 *    avg_per_capita_simple  各省人均的算术平均 —— 作为副信息对照
 */
import { computed, onMounted, ref, watch } from 'vue'

import { getSummary } from '@/api/tourism'
import { fmt } from '@/utils/echartsTheme'

const props = defineProps({
    /** 统计年份，由父组件（Dashboard）传入 */
    year: { type: Number, default: null },
})

const summary = ref(null)
const errorMsg = ref('')

/* ==================== 数据加载 ==================== */
async function load() {
    if (props.year === null || props.year === undefined) return

    errorMsg.value = ''
    try {
        summary.value = await getSummary({ year: props.year, stat_type: 'annual' })
    } catch (e) {
        summary.value = null
        errorMsg.value = `加载失败：${e.message}`
    }
}

onMounted(load)
watch(() => props.year, load)

/* ==================== 卡片数据 ==================== */
const cards = computed(() => {
    const s = summary.value

    // 数据未就绪时展示占位，保持布局不跳动
    if (!s) {
        return [
            { key: 'visitor', label: '总客流', value: '--', unit: '亿人次', caliber: '', extra: '加载中...' },
            { key: 'revenue', label: '总收入', value: '--', unit: '万亿元', caliber: '', extra: '加载中...' },
            { key: 'top', label: '收入第一省', value: '--', unit: '', caliber: '', extra: '加载中...' },
            { key: 'percapita', label: '人均消费', value: '--', unit: '元', caliber: '', extra: '加载中...' },
        ]
    }

    return [
        {
            key: 'visitor',
            label: '总客流',
            value: fmt(s.total_visitor_yi, 2),
            unit: '亿人次',
            caliber: s.caliber,
            extra: `折合 ${fmt(s.total_visitor, 0)} 万人次｜覆盖 ${s.province_count} 个省份`,
        },
        {
            key: 'revenue',
            label: '总收入',
            value: fmt(s.total_revenue_wanyi, 4),
            unit: '万亿元',
            caliber: s.caliber,
            extra: `折合 ${fmt(s.total_revenue, 0)} 亿元`,
        },
        {
            key: 'top',
            label: '收入第一省',
            value: s.top_province ? s.top_province.name : '--',
            unit: '',
            caliber: '',
            extra: s.top_province
                ? `${s.top_province.metric_name} ${fmt(s.top_province.value, 0)} 亿元`
                : '',
        },
        {
            key: 'percapita',
            label: '人均消费',
            value: fmt(s.avg_per_capita, 2),
            unit: '元',
            caliber: '加权口径',
            extra: `各省算术平均 ${fmt(s.avg_per_capita_simple, 2)} 元`,
        },
    ]
})
</script>

<style scoped>
.summary-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    width: 100%;
    height: 100%;
}

.summary-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 6px;
    padding: 0 20px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid #1e3a8a;
    border-left: 3px solid #409eff;
    border-radius: 6px;
    /* 左侧高亮条向外扩散的微光 */
    box-shadow: inset 0 0 24px rgba(64, 158, 255, 0.06);
    transition: border-color 0.2s, box-shadow 0.2s;
}

.summary-card:hover {
    border-color: #409eff;
    box-shadow: inset 0 0 28px rgba(64, 158, 255, 0.16), 0 0 12px rgba(64, 158, 255, 0.2);
}

/* 加载失败时左侧条变红，便于一眼看出是接口问题而非无数据 */
.summary-card.is-error {
    border-left-color: #ee6666;
}

.card-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.65);
}

.card-caliber {
    padding: 1px 6px;
    font-size: 11px;
    color: #91cc75;
    border: 1px solid rgba(145, 204, 117, 0.5);
    border-radius: 3px;
}

.card-value {
    display: flex;
    align-items: baseline;
    gap: 6px;
}

.card-number {
    font-size: 30px;
    font-weight: 700;
    color: #409eff;
    font-variant-numeric: tabular-nums;
    text-shadow: 0 0 14px rgba(64, 158, 255, 0.45);
    white-space: nowrap;
}

.card-unit {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.65);
}

.card-extra {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.4);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
