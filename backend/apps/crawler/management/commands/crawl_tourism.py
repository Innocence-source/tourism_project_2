"""自定义管理命令：爬取文旅厅节假日旅游统计数据。

用法：
    # 默认：抓取内置演示页面（data/sample_page.html），走完整的 HTTP/解析/清洗/入库链路
    python manage.py crawl_tourism

    # 抓取真实省文旅厅公报页面
    python manage.py crawl_tourism --url "https://xxx.gov.cn/xxx.html" \
        --province 广东省 --stat-type national_day --year 2024

    # 跳过网络，直接用示例数据兜底（演示/答辩最稳妥的用法）
    python manage.py crawl_tourism --sample

    # 强制清空后重新抓取
    python manage.py crawl_tourism --flush

内置安全机制：
    1. 抓取失败（页面改版 / URL 失效 / 网络不通）自动回落读取 sample_data.json，
       保证「爬虫命令永远能跑通、永远有数据」，避免答辩现场翻车；
    2. 所有入库使用 update_or_create，重复执行不会产生重复记录；
    3. 每次执行都向 crawl_log 写一条记录，保留完整采集痕迹。
"""
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.crawler import utils
from apps.region.models import Region
from apps.tourism.models import TourismStat, CityRanking


class Command(BaseCommand):
    help = '爬取省级文旅厅节假日旅游统计公报并入库（失败自动回落示例数据）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url', dest='url', default=None,
            help='目标页面地址；不传则使用内置演示页面 data/sample_page.html',
        )
        parser.add_argument(
            '--province', dest='province', default='广东省',
            help='数据归属省份，默认 广东省',
        )
        parser.add_argument(
            '--stat-type', dest='stat_type', default='national_day',
            choices=[c[0] for c in TourismStat.STAT_TYPE_CHOICES],
            help='统计口径，默认 national_day（国庆）',
        )
        parser.add_argument(
            '--year', dest='year', type=int, default=2024,
            help='统计年份，默认 2024',
        )
        parser.add_argument(
            '--sample', action='store_true',
            help='跳过网络抓取，直接读取 data/sample_data.json 灌库',
        )
        parser.add_argument(
            '--flush', action='store_true',
            help='抓取前清空 region / tourism_stat / city_ranking 三张业务表',
        )
        parser.add_argument(
            '--no-sleep', action='store_true',
            help='关闭每次请求之间的 1 秒间隔（不建议，可能给目标站点造成压力）',
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        url = options['url']
        province = options['province']
        stat_type = options['stat_type']
        year = options['year']
        use_sample = options['sample']
        no_sleep = options['no_sleep']

        self.stdout.write(self.style.MIGRATE_HEADING('== 旅游数据爬虫 =='))

        # ---------- 可选：清空业务表 ----------
        if options.get('flush'):
            self.stdout.write(self.style.WARNING('  --flush：正在清空既有业务数据（TRUNCATE）...'))
            utils.flush_business_tables()
            self.stdout.write('  已清空 region / tourism_stat / city_ranking，自增 ID 已重置')

        # ---------- 模式一：直接使用示例数据兜底 ----------
        if use_sample:
            self.stdout.write('  模式：--sample（跳过网络，直接导入示例数据）')
            self._fallback_to_sample('人工指定 --sample 参数')
            return

        # ---------- 模式二：真实抓取链路 ----------
        target_url = url or str(utils.SAMPLE_PAGE_FILE)
        source_label = target_url if url else f'内置演示页面({utils.SAMPLE_PAGE_FILE.name})'

        self.stdout.write(f'  目标页面：{target_url}')
        self.stdout.write(f'  归属省份：{province}')
        self.stdout.write(f'  统计口径：{stat_type}（{dict(TourismStat.STAT_TYPE_CHOICES).get(stat_type, "-")}）')
        self.stdout.write(f'  统计年份：{year}')
        self.stdout.write('')

        try:
            # 1) 抓取（爬虫礼仪：请求前先等待）
            if not no_sleep:
                time.sleep(utils.CRAWL_DELAY)
            self.stdout.write('  [1/3] 正在获取页面...')
            html = utils.fetch_html(target_url)
            self.stdout.write(self.style.SUCCESS(f'        获取成功，HTML 长度 {len(html)} 字符'))

            # 2) 解析 + 清洗
            self.stdout.write('  [2/3] 正在解析表格并清洗数据...')
            records = utils.parse_holiday_table(
                html,
                province_name=province,
                stat_type=stat_type,
                year=year,
                source=f'{province}文化和旅游厅 {year} 年公报｜{target_url}',
            )
            self.stdout.write(self.style.SUCCESS(f'        解析出 {len(records)} 条记录'))

            # 3) 入库
            self.stdout.write('  [3/3] 正在写入数据库...')
            with transaction.atomic():
                result = utils.save_records(
                    records, stat_type=stat_type, year=year, province_name=province
                )

            msg = (f'抓取成功：{source_label}｜解析 {len(records)} 条，'
                   f'新增 {result["created"]} 条，更新 {result["updated"]} 条')
            utils.log_crawl(source_label, 'success', msg)

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'== {msg} =='))
            self._print_summary()

        except Exception as exc:                       # noqa: BLE001
            # ---------- 抓取失败：记录失败日志，并自动回落示例数据 ----------
            fail_msg = f'抓取/解析失败：{exc}'
            utils.log_crawl(source_label, 'failed', fail_msg)
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'  {fail_msg}'))
            self._fallback_to_sample(str(exc))

    # ------------------------------------------------------------------
    def _fallback_to_sample(self, reason):
        """兜底：读取 sample_data.json 并灌库，保证系统始终有数据可用。"""
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(f'  触发兜底机制（原因：{reason}）'))
        self.stdout.write('  正在读取示例数据 data/sample_data.json ...')

        try:
            payload = utils.load_sample_payload()
        except Exception as exc:                       # noqa: BLE001
            utils.log_crawl('crawl_tourism.fallback', 'failed', f'兜底数据读取失败：{exc}')
            raise CommandError(f'兜底数据读取失败：{exc}')

        self.stdout.write(f'  数据声明：{payload.get("note", "（无）")}')

        with transaction.atomic():
            result = utils.import_sample_payload(payload, verbose=False)

        msg = (f'兜底导入完成：地区 {result["regions"]} 条，'
               f'旅游统计 {result["stats"]} 条，城市榜单 {result["city_rankings"]} 条')
        utils.log_crawl('crawl_tourism.fallback', 'partial',
                        f'{msg}｜触发原因：{reason}')

        self.stdout.write(self.style.SUCCESS(f'  {msg}'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            '  注意：以上数据来自示例文件，已标注为「示例数据」，不可作为真实统计结果引用。'
        ))
        self._print_summary()

    # ------------------------------------------------------------------
    def _print_summary(self):
        """打印当前库内数据概况，方便肉眼确认。"""
        self.stdout.write('')
        self.stdout.write('  当前库内概况：')
        self.stdout.write(f'    地区        {Region.objects.count()} 条'
                          f'（省份 {Region.objects.filter(level=1).count()}，'
                          f'城市 {Region.objects.filter(level=2).count()}）')
        self.stdout.write(f'    旅游统计    {TourismStat.objects.count()} 条')
        self.stdout.write(f'    城市榜单    {CityRanking.objects.count()} 条')
