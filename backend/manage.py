#!/usr/bin/env python
"""Django 命令行管理入口。

用法示例：
    python manage.py runserver 8001        # 启动开发服务器（8001 端口）
    python manage.py makemigrations        # 生成迁移文件
    python manage.py migrate               # 执行迁移建表
    python manage.py createsuperuser       # 创建后台管理员
    python manage.py crawl_tourism         # 运行爬虫（第三阶段实现）
"""
import os
import sys


def main():
    """运行管理命令。"""
    # 指定默认配置文件位置
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tourism_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django，请确认：\n"
            "  1. 已激活虚拟环境：source .venv/Scripts/activate （Windows Git Bash）\n"
            "  2. 已安装依赖：pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
