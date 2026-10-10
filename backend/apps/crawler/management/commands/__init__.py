"""commands 子包：存放自定义管理命令。

第二阶段将新增 crawl_tourism.py，支持：
    python manage.py crawl_tourism               # 抓取默认示例页面
    python manage.py crawl_tourism --url <URL>   # 抓取指定真实页面
    python manage.py crawl_tourism --sample      # 直接读取 sample_data.json 兜底
"""
