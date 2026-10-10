"""自定义管理命令：导入示例数据。

用法：
    python manage.py import_sample_data                 # 导入 data/sample_data.json
    python manage.py import_sample_data --file D:/x.json  # 指定文件
    python manage.py import_sample_data --flush         # 导入前清空业务表

说明：
    本命令与爬虫命令解耦 —— 爬虫负责「采集」，本命令负责「灌入演示数据」。
    两者都调用 apps/crawler/utils.py 中的同一套入库逻辑，保证行为一致。
    所有写入均为 update_or_create，重复执行不会产生重复数据。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.crawler import utils
from apps.tourism.models import TourismStat, CityRanking
from apps.region.models import Region


class Command(BaseCommand):
    help = '导入示例旅游数据（data/sample_data.json），幂等可重复执行'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', dest='file', default=None,
            help='示例数据 JSON 路径，默认 backend/data/sample_data.json',
        )
        parser.add_argument(
            '--flush', action='store_true',
            help='导入前清空 region / tourism_stat / city_ranking 三张业务表',
        )

    def handle(self, *args, **options):
        file_path = options.get('file')
        source_label = 'import_sample_data'

        try:
            payload = utils.load_sample_payload(file_path)
        except Exception as exc:                       # noqa: BLE001
            utils.log_crawl(source_label, 'failed', f'读取示例数据失败：{exc}')
            raise CommandError(f'读取示例数据失败：{exc}')

        self.stdout.write(self.style.MIGRATE_HEADING('== 导入示例数据 =='))
        self.stdout.write(f'  数据文件：{file_path or utils.SAMPLE_DATA_FILE}')
        self.stdout.write(f'  数据声明：{payload.get("note", "（无）")}')
        if payload.get('disclaimer'):
            self.stdout.write(f'  免责说明：{payload["disclaimer"]}')
        self.stdout.write('')

        # 可选：清空业务表（便于反复演示）
        if options.get('flush'):
            self.stdout.write(self.style.WARNING('  --flush：正在清空既有业务数据（TRUNCATE）...'))
            utils.flush_business_tables()
            self.stdout.write(self.style.WARNING(
                '  已清空 region / tourism_stat / city_ranking，自增 ID 已重置'
            ))

        try:
            with transaction.atomic():
                result = utils.import_sample_payload(payload, verbose=True)
        except Exception as exc:                       # noqa: BLE001
            utils.log_crawl(source_label, 'failed', f'导入失败：{exc}')
            raise CommandError(f'导入失败：{exc}')

        msg = (f'导入完成：地区 {result["regions"]} 条，'
               f'旅游统计 {result["stats"]} 条，城市榜单 {result["city_rankings"]} 条')
        utils.log_crawl(source_label, 'success', msg)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'== 完成：{msg} =='))
        self.stdout.write(f'  当前库内：地区 {Region.objects.count()} 条，'
                          f'旅游统计 {TourismStat.objects.count()} 条，'
                          f'城市榜单 {CityRanking.objects.count()} 条')
