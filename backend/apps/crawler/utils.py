"""
爬虫工具集
=========

职责划分：
    1. HTML 获取      —— fetch_html()：支持 http(s) 抓取与本地文件读取
    2. 数据清洗        —— clean_number() / calc_per_capita()：去千分位、统一单位、算人均
    3. 表格解析        —— parse_holiday_table()：把文旅厅公报表格解析为标准化记录
    4. 数据入库        —— save_records()：update_or_create 幂等写入
    5. 采集留痕        —— log_crawl()：每次采集写一条 crawl_log
    6. 兜底数据源      —— import_sample_payload()：读取 sample_data.json 灌库

设计说明（重要）：
    真实省文旅厅公报页面存在三个不可控因素：URL 逐年失效、正文以 PDF 附件为主、
    页面结构随改版变动。因此本模块采用「可插拔解析器」思路：
    解析规则集中在 parse_holiday_table() 中，页面结构变化时只需改这一个函数；
    同时内置 data/sample_page.html 作为结构一致的演示页面，保证系统随时可跑通。
"""
from __future__ import annotations

import json
import re
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from apps.region.models import Region
from apps.tourism.models import TourismStat, CityRanking, CrawlLog

# ============================================================
# 路径与常量
# ============================================================
# utils.py 位于 backend/apps/crawler/utils.py，向上三级即 backend/
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
SAMPLE_DATA_FILE = DATA_DIR / 'sample_data.json'
SAMPLE_PAGE_FILE = DATA_DIR / 'sample_page.html'

# 伪装浏览器，避免被简单 UA 黑名单拦截
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
)
REQUEST_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

# 抓取间隔（秒），遵守爬虫礼仪，避免给目标站点造成压力
CRAWL_DELAY = 1.0

PARSER_ERROR_HINT = (
    '页面结构与解析规则不匹配。请检查目标页面是否改版，'
    '或改用 --sample 参数读取示例数据。'
)


# ============================================================
# 一、数据清洗
# ============================================================
def clean_number(raw):
    """把网页上的脏数字清洗为 Decimal。

    可处理的情况：
        '5,325.30'      -> Decimal('5325.30')      千分位逗号
        '5,325.30万'     -> Decimal('5325.30')      单位后缀
        '680.44亿元'     -> Decimal('680.44')
        '8.6%'          -> Decimal('8.6')
        '－' '—' '-' '' -> None                     缺失值
        '5325.3人次'     -> Decimal('5325.3')

    :param raw: 原始文本，可为 None
    :return: Decimal 或 None
    """
    if raw is None:
        return None

    text = str(raw).strip()
    if not text:
        return None

    # 常见的"无数据"占位符
    if text in {'-', '—', '－', '--', '/', '无', '略', 'N/A', 'n/a'}:
        return None

    # 去掉千分位逗号、空格、全角空格
    text = text.replace(',', '').replace('，', '').replace(' ', '').replace('\u3000', '')

    # 提取第一个数字（含负号与小数点），自动剥离 万/亿/元/人次/%/等 单位字符
    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return None

    try:
        return Decimal(match.group())
    except InvalidOperation:
        return None


def calc_per_capita(visitor_count, revenue):
    """计算人均消费（元）。

    换算原理：
        客流单位是万人次，收入单位是亿元，
        人均 = 收入(亿) x 1e8 / (客流(万) x 1e4) = 收入 x 10000 / 客流

    :param visitor_count: 接待游客，万人次（Decimal / 数值 / 字符串均可）
    :param revenue: 旅游收入，亿元
    :return: Decimal（保留 2 位）或 None
    """
    if visitor_count is None or revenue is None:
        return None

    vc = visitor_count if isinstance(visitor_count, Decimal) else clean_number(visitor_count)
    rv = revenue if isinstance(revenue, Decimal) else clean_number(revenue)

    if vc is None or rv is None or vc == 0:
        return None

    return (rv * Decimal('10000') / vc).quantize(Decimal('0.01'))


def to_decimal(value, places='0.01'):
    """把任意数值安全转换为 Decimal，并统一小数位。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        d = value
    else:
        try:
            d = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None
    quant = Decimal(places) if isinstance(places, str) else places
    return d.quantize(quant)


# ============================================================
# 二、HTML 获取
# ============================================================
def fetch_html(url, timeout=15, retries=2):
    """获取页面 HTML。

    - 传入 http(s) 地址：使用 requests 抓取，失败自动重试
    - 传入 file:// 地址或本地路径：直接读文件（用于离线演示）

    :param url: 目标地址
    :param timeout: 单次请求超时（秒）
    :param retries: 重试次数
    :return: HTML 文本
    :raises RuntimeError: 全部重试失败时抛出
    """
    # ---- 本地文件分支 ----
    if url.startswith('file://') or (not url.startswith(('http://', 'https://'))):
        local_path = Path(url.replace('file://', '').replace('/', '\\') if url.startswith('file://') else url)
        if not local_path.exists():
            # 允许直接传逻辑名 sample_page.html
            local_path = DATA_DIR / url
        if not local_path.exists():
            raise RuntimeError(f'本地文件不存在：{local_path}')
        return local_path.read_text(encoding='utf-8')

    # ---- 网络分支 ----
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
            resp.raise_for_status()
            # 部分政务站点未声明编码，用 apparent_encoding 兜底，避免中文乱码
            if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
                resp.encoding = resp.apparent_encoding or 'utf-8'
            return resp.text
        except Exception as exc:                      # noqa: BLE001 —— 网络异常类型繁多，统一兜住
            last_error = exc
            if attempt < retries:
                time.sleep(CRAWL_DELAY)
    raise RuntimeError(f'抓取失败（已重试 {retries} 次）：{url}｜{last_error}')


# ============================================================
# 三、表格解析（可插拔解析器）
# ============================================================
# 表头关键词 -> 内部字段名。页面改版时只需调整这张映射表
HEADER_KEYWORDS = {
    'visitor_count': ('接待游客', '接待人数', '游客人次', '旅游人次', '客流量', '游客接待'),
    'revenue': ('旅游收入', '旅游总花费', '旅游消费', '旅游花费', '收入'),
    'yoy': ('同比', '增幅', '增长率', '增速'),
}
# 地区列关键词
REGION_KEYWORDS = ('地区', '地市', '城市', '行政区', '省份', '市', '州')
# 表示"全省/全市汇总"的关键词，这类行归属到省份本身
TOTAL_KEYWORDS = ('全省合计', '全省总计', '全市合计', '合计', '总计', '全省', '全市')


def _match_column(headers, field):
    """在表头文本列表中，找到属于 field 的列下标，返回 None 表示未找到。"""
    for idx, text in enumerate(headers):
        if not text:
            continue
        for kw in HEADER_KEYWORDS[field]:
            if kw in text:
                return idx
    return None


def parse_holiday_table(html, province_name, stat_type, year, source):
    """解析省级文旅厅节假日公报中的统计表格。

    标准输出记录格式：
        {
            'region_name': '广州市',
            'is_province_total': False,     # True 表示该行是"全省合计"，归属到省份
            'visitor_count': Decimal('1180.50'),
            'revenue': Decimal('155.83'),
            'per_capita': Decimal('1319.89'),
            'yoy_visitor': Decimal('9.2'),
            'data_source': '...',
        }

    :param html: 页面 HTML 文本
    :param province_name: 省份名称，如 '广东省'
    :param stat_type: 统计口径，如 'national_day'
    :param year: 年份
    :param source: 数据来源描述，写入 data_source 字段
    :return: 记录列表
    :raises RuntimeError: 未找到表格或无法识别表头
    """
    soup = BeautifulSoup(html, 'lxml')

    # 优先抓取带 stat-table 类名的表格，退化时取正文中第一个表格
    table = soup.find('table', class_='stat-table') or soup.find('table')
    if table is None:
        raise RuntimeError(f'页面中未找到表格。{PARSER_ERROR_HINT}')

    # ---------- 解析表头 ----------
    header_cells = table.find_all('th')
    if not header_cells:
        first_row = table.find('tr')
        header_cells = first_row.find_all('td') if first_row else []
    headers = [c.get_text(strip=True) for c in header_cells]

    visitor_idx = _match_column(headers, 'visitor_count')
    revenue_idx = _match_column(headers, 'revenue')
    yoy_idx = _match_column(headers, 'yoy')

    if visitor_idx is None or revenue_idx is None:
        raise RuntimeError(
            f'表头未识别到「接待游客」「旅游收入」列，实际表头：{headers}。{PARSER_ERROR_HINT}'
        )

    # ---------- 解析数据行 ----------
    records = []
    for tr in table.find_all('tr'):
        cells = tr.find_all('td')
        if len(cells) <= max(visitor_idx, revenue_idx):
            continue

        region_name = cells[0].get_text(strip=True)
        if not region_name:
            continue

        visitor = clean_number(cells[visitor_idx].get_text(strip=True))
        revenue = clean_number(cells[revenue_idx].get_text(strip=True))
        yoy = clean_number(cells[yoy_idx].get_text(strip=True)) if yoy_idx is not None and len(cells) > yoy_idx else None

        # 客流与收入都为空，视为无效行
        if visitor is None and revenue is None:
            continue

        is_total = any(kw in region_name for kw in TOTAL_KEYWORDS)
        # "全省合计" 这类行归属到省份自身
        target_name = province_name if is_total else region_name

        records.append({
            'region_name': target_name,
            'is_province_total': is_total,
            'visitor_count': visitor,
            'revenue': revenue,
            'per_capita': calc_per_capita(visitor, revenue),
            'yoy_visitor': yoy,          # 公报表格通常只给一个同比，先记在客流同比上
            'yoy_revenue': None,
            'data_source': source,
        })

    if not records:
        raise RuntimeError(f'表格解析结果为空。{PARSER_ERROR_HINT}')

    return records


# ============================================================
# 四、地区与统计入库
# ============================================================
def get_or_create_province(name, longitude=None, latitude=None):
    """按名称取得（或创建）省份记录。"""
    region, _ = Region.objects.get_or_create(
        name=name,
        level=Region.LEVEL_PROVINCE,
        defaults={'longitude': to_decimal(longitude, '0.000001'),
                  'latitude': to_decimal(latitude, '0.000001')},
    )
    return region


def get_or_create_city(name, province, longitude=None, latitude=None):
    """按名称取得（或创建）城市记录，并挂到所属省份下。"""
    city, created = Region.objects.get_or_create(
        name=name,
        level=Region.LEVEL_CITY,
        defaults={'parent': province,
                  'longitude': to_decimal(longitude, '0.000001'),
                  'latitude': to_decimal(latitude, '0.000001')},
    )
    # 已存在但缺少父级归属时补齐
    if not created and city.parent_id is None:
        city.parent = province
        city.save(update_fields=['parent'])
    return city


def resolve_region(region_name, province_name, is_province_total):
    """根据名称解析出 Region 实例。

    规则：
        - is_province_total=True    -> 直接取省份
        - 名称等于省份名            -> 取省份
        - 其余                      -> 取/建该省下的城市
    """
    if is_province_total or region_name == province_name:
        province = get_or_create_province(province_name)
        return province, province

    province = get_or_create_province(province_name)
    city = get_or_create_city(region_name, province)
    return city, province


def save_records(records, stat_type, year, province_name, verbose=True):
    """把解析结果幂等写入 tourism_stat。

    :return: {'created': int, 'updated': int}
    """
    created = updated = 0
    for rec in records:
        region, _province = resolve_region(
            rec['region_name'], province_name, rec['is_province_total']
        )
        _obj, is_created = TourismStat.objects.update_or_create(
            region=region,
            stat_type=stat_type,
            year=year,
            defaults={
                'visitor_count': rec['visitor_count'],
                'revenue': rec['revenue'],
                'per_capita': rec['per_capita'],
                'yoy_visitor': rec['yoy_visitor'],
                'yoy_revenue': rec['yoy_revenue'],
                'data_source': rec['data_source'],
            },
        )
        if is_created:
            created += 1
        else:
            updated += 1
        if verbose:
            flag = '新增' if is_created else '更新'
            print(f'    [{flag}] {region.name} {year} {stat_type} '
                  f'客流={rec["visitor_count"]} 万  收入={rec["revenue"]} 亿  人均={rec["per_capita"]} 元')

    return {'created': created, 'updated': updated}


# ============================================================
# 五、采集日志
# ============================================================
def log_crawl(source, status, message):
    """写入一条爬虫日志。status: success / failed / partial"""
    return CrawlLog.objects.create(source=source, status=status, message=message)


# ============================================================
# 六、兜底：读取并导入示例数据
# ============================================================
def load_sample_payload(path=None):
    """读取 sample_data.json，返回原始 dict。"""
    file_path = Path(path) if path else SAMPLE_DATA_FILE
    if not file_path.exists():
        raise RuntimeError(f'示例数据文件不存在：{file_path}')
    with file_path.open('r', encoding='utf-8') as f:
        return json.load(f)


def import_sample_payload(payload, verbose=True):
    """把 sample_data.json 的内容灌入数据库（幂等）。

    导入顺序：地区 -> 旅游统计 -> 城市榜单

    :return: {'regions': n, 'stats': n, 'city_rankings': n}
    """
    # ---------- 1. 地区 ----------
    prov_map = {}
    city_map = {}
    for item in payload.get('regions', []):
        province = get_or_create_province(
            item['name'], item.get('longitude'), item.get('latitude')
        )
        prov_map[item['name']] = province
        for city_item in item.get('cities', []):
            city = get_or_create_city(
                city_item['name'], province,
                city_item.get('longitude'), city_item.get('latitude'),
            )
            city_map[city_item['name']] = city

    if verbose:
        print(f'  地区：省份 {len(prov_map)} 个，城市 {len(city_map)} 个')

    # ---------- 2. 旅游统计 ----------
    stat_created = stat_updated = 0
    for s in payload.get('stats', []):
        region = prov_map.get(s['region']) or city_map.get(s['region'])
        if region is None:
            if verbose:
                print(f'    [跳过] 未找到地区：{s["region"]}')
            continue

        visitor = to_decimal(s.get('visitor_count'))
        revenue = to_decimal(s.get('revenue'))
        per_capita = to_decimal(s.get('per_capita')) or calc_per_capita(visitor, revenue)

        _obj, is_created = TourismStat.objects.update_or_create(
            region=region,
            stat_type=s['stat_type'],
            year=s['year'],
            defaults={
                'visitor_count': visitor,
                'revenue': revenue,
                'per_capita': per_capita,
                'yoy_visitor': to_decimal(s.get('yoy_visitor')),
                'yoy_revenue': to_decimal(s.get('yoy_revenue')),
                'data_source': (s.get('data_source') or '')[:100],
            },
        )
        stat_created += int(is_created)
        stat_updated += int(not is_created)

    if verbose:
        print(f'  旅游统计：新增 {stat_created} 条，更新 {stat_updated} 条')

    # ---------- 3. 城市榜单 ----------
    rank_created = rank_updated = 0
    for c in payload.get('city_rankings', []):
        city = city_map.get(c['city'])
        if city is None:
            # 榜单里出现了未在 regions 中定义的城市，兜底创建（挂在同名省份下不可行，故跳过）
            if verbose:
                print(f'    [跳过] 榜单城市未定义：{c["city"]}')
            continue

        visitor = to_decimal(c.get('visitor_count'))
        revenue = to_decimal(c.get('revenue'))
        _obj, is_created = CityRanking.objects.update_or_create(
            city=city,
            period=c['period'],
            defaults={
                'rank_no': c.get('rank_no'),
                'visitor_count': visitor,
                'revenue': revenue,
                'per_capita': to_decimal(c.get('per_capita')) or calc_per_capita(visitor, revenue),
            },
        )
        rank_created += int(is_created)
        rank_updated += int(not is_created)

    if verbose:
        print(f'  城市榜单：新增 {rank_created} 条，更新 {rank_updated} 条')

    return {
        'regions': len(prov_map) + len(city_map),
        'stats': stat_created + stat_updated,
        'city_rankings': rank_created + rank_updated,
    }


# ============================================================
# 七、业务表清空
# ============================================================
def flush_business_tables():
    """清空三张业务表并重置自增 ID。

    为什么不用 ORM 的 .delete()：
        DELETE 语句不会重置 InnoDB 的 AUTO_INCREMENT 计数器，
        清空后新插入数据的 id 会从旧值继续（例如省份 id 从 49 起），
        导致演示与接口文档中的 region_id=1 对不上。
        改用 TRUNCATE 可直接把自增归零。

    注意：必须先关闭外键检查，否则因 city_ranking / tourism_stat
         引用了 region，TRUNCATE 会报 1701 错误。
        不清空 crawl_log —— 采集日志属于审计痕迹，应当保留。
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
        for table in ('city_ranking', 'tourism_stat', 'region'):
            cursor.execute(f'TRUNCATE TABLE `{table}`')
        cursor.execute('SET FOREIGN_KEY_CHECKS = 1')


def flush_summary():
    """返回清空后的行数概览，供命令回显使用。"""
    return (
        CityRanking.objects.count(),
        TourismStat.objects.count(),
        Region.objects.count(),
    )
