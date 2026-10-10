"""
WSGI 部署入口

开发环境由 manage.py runserver 使用；
生产环境可通过 gunicorn / uWSGI 加载本模块（本项目不要求部署）。
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tourism_project.settings')

application = get_wsgi_application()
